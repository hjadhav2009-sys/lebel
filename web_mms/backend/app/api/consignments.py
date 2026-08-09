from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.auth import CurrentPrincipal,require_roles
from app.db.session import get_db
from app.models import AuditEvent, Consignment, ConsignmentIssue, ConsignmentLine, Marketplace, MarketplaceAccount, PrintJob, PrintJobLine
from app.schemas import BulkSelection, BulkStatus, ConsignmentCreate, ConsignmentLinePatch, ConsignmentPatch
from app.services.consignment_import_service import ConsignmentImportService, parse_consignment
from app.services.consignment_validation import ConsignmentValidationService
from app.services.label_data_service import ConsignmentLabelDataService

router = APIRouter(prefix="/consignments", tags=["consignments"])
line_router = APIRouter(prefix="/consignment-lines", tags=["consignment-lines"])
STATUSES = {"draft", "open", "partially_printed", "completed", "archived", "cancelled"}


def _consignment_dict(row: Consignment, counts=None):
    values = counts or {}
    return {"id": str(row.id), "account_id": str(row.account_id), "account_name": row.account.name,
        "marketplace": row.marketplace.value, "name": row.name, "reference_number": row.reference_number,
        "source_file_name": row.source_file_name, "source_type": row.source_type, "status": row.status,
        "created_by_id": str(row.created_by_id) if row.created_by_id else None, "created_at": row.created_at,
        "updated_at": row.updated_at, "completed_at": row.completed_at, **values}


@router.get("")
def list_consignments(marketplace: str | None = None, account_id: UUID | None = None, status: str | None = None,
    search: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), db: Session = Depends(get_db)):
    query = select(Consignment).options(selectinload(Consignment.account))
    if marketplace: query = query.where(Consignment.marketplace == Marketplace(marketplace.casefold()))
    if account_id: query = query.where(Consignment.account_id == account_id)
    if status: query = query.where(Consignment.status == status)
    if search:
        term = f"%{search.strip()}%"; query = query.where(or_(Consignment.name.ilike(term), Consignment.reference_number.ilike(term)))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = list(db.scalars(query.order_by(Consignment.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)).all())
    items = []
    for row in rows:
        state_rows = db.execute(select(ConsignmentLine.workflow_state, func.count()).where(ConsignmentLine.consignment_id == row.id).group_by(ConsignmentLine.workflow_state)).all()
        states: dict[str, int] = {state: count for state, count in state_rows}
        items.append(_consignment_dict(row, {"rows": sum(states.values()), "to_print": states.get("to_print", 0), "blocked": states.get("blocked", 0), "printed": states.get("printed", 0)}))
    return {"items": items, "total": total, "page": page, "page_size": page_size, "page_count": ceil(total / page_size) if total else 0}


@router.post("", status_code=201)
def create_consignment(payload: ConsignmentCreate, db: Session = Depends(get_db)):
    account = db.get(MarketplaceAccount, payload.account_id)
    try: marketplace = Marketplace(payload.marketplace.casefold())
    except ValueError as exc: raise HTTPException(422, detail={"code": "INVALID_MARKETPLACE", "message": "Unsupported marketplace."}) from exc
    if not account or account.marketplace != marketplace: raise HTTPException(422, detail={"code": "ACCOUNT_MARKETPLACE_MISMATCH", "message": "Account does not belong to this marketplace."})
    row = Consignment(account_id=account.id, marketplace=marketplace, name=payload.name, reference_number=payload.reference_number, status="draft", source_type="manual")
    db.add(row); db.flush(); db.add(AuditEvent(entity_type="consignment", entity_id=str(row.id), action="created", changes={}, context={"marketplace": marketplace.value})); db.commit(); db.refresh(row)
    row.account = account
    return _consignment_dict(row)


@router.get("/{consignment_id}")
def get_consignment(consignment_id: UUID, db: Session = Depends(get_db)):
    row = db.scalar(select(Consignment).where(Consignment.id == consignment_id).options(selectinload(Consignment.account)))
    if not row: raise HTTPException(404, detail={"code": "CONSIGNMENT_NOT_FOUND", "message": "Consignment not found."})
    return _consignment_dict(row)


@router.patch("/{consignment_id}")
def patch_consignment(consignment_id: UUID, payload: ConsignmentPatch, db: Session = Depends(get_db)):
    row = db.get(Consignment, consignment_id)
    if not row: raise HTTPException(404, detail={"code": "CONSIGNMENT_NOT_FOUND", "message": "Consignment not found."})
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("status") and changes["status"] not in STATUSES: raise HTTPException(422, detail={"code": "INVALID_STATUS", "message": "Unsupported consignment status."})
    old = {key: getattr(row, key) for key in changes}
    for key, value in changes.items(): setattr(row, key, value)
    if row.status in {"completed", "archived"}: row.completed_at = row.completed_at or datetime.now(timezone.utc)
    db.add(AuditEvent(entity_type="consignment", entity_id=str(row.id), action="updated", changes={key: {"old": old[key], "new": value} for key, value in changes.items()}, context={}))
    db.commit(); return {"id": str(row.id), "status": row.status}


@router.post("/{consignment_id}/preview-upload")
async def preview_upload(consignment_id: UUID, file: UploadFile = File(...), db: Session = Depends(get_db)):
    row = db.get(Consignment, consignment_id)
    if not row: raise HTTPException(404, detail={"code": "CONSIGNMENT_NOT_FOUND", "message": "Consignment not found."})
    try: parsed = parse_consignment(file.filename or "upload.xlsx", await file.read(), row.marketplace)
    except ValueError as exc: raise HTTPException(422, detail={"code": "UNSUPPORTED_CONSIGNMENT_FILE", "message": str(exc)}) from exc
    return {"file": parsed.filename, "sheet": parsed.sheet, "detected_type": parsed.detected_type, "header_row": parsed.header_row,
        "rows": len(parsed.rows), "recognized_columns": parsed.recognized_columns, "warnings": parsed.warnings, "file_sha256": parsed.sha256}


@router.post("/{consignment_id}/import-upload")
async def import_upload(consignment_id: UUID, file: UploadFile = File(...), db: Session = Depends(get_db)):
    row = db.scalar(select(Consignment).where(Consignment.id == consignment_id).options(selectinload(Consignment.account)))
    if not row: raise HTTPException(404, detail={"code": "CONSIGNMENT_NOT_FOUND", "message": "Consignment not found."})
    if db.scalar(select(func.count(ConsignmentLine.id)).where(ConsignmentLine.consignment_id == row.id)):
        raise HTTPException(409, detail={"code": "CONSIGNMENT_ALREADY_IMPORTED", "message": "Start a new consignment instead of replacing historical lines."})
    try: parsed = parse_consignment(file.filename or "upload.xlsx", await file.read(), row.marketplace); summary = ConsignmentImportService(db).apply(row, parsed)
    except ValueError as exc: raise HTTPException(422, detail={"code": "INVALID_CONSIGNMENT_FILE", "message": str(exc)}) from exc
    db.add(AuditEvent(entity_type="consignment", entity_id=str(row.id), action="source_imported", changes=summary, context={"sha256": parsed.sha256, "file": parsed.filename})); db.commit()
    return summary


def _line_dict(line: ConsignmentLine, issue_codes=None):
    return {"id": str(line.id), "consignment_id": str(line.consignment_id), "product_id": str(line.product_id) if line.product_id else None,
        "source_row": line.source_row, "merchant_sku": line.merchant_sku, "asin": line.asin, "fnsku": line.fnsku, "fsn": line.fsn,
        "listing_id": line.listing_id, "title": line.label_overrides.get("title") or line.title_snapshot, "brand": line.label_overrides.get("brand") or line.brand_snapshot,
        "format_key": line.format_key, "mrp": line.mrp_override if line.mrp_override is not None else line.mrp_catalog, "mrp_source": "override" if line.mrp_override is not None else line.mrp_source,
        "net_quantity_value": line.net_quantity_value, "net_quantity_unit": line.net_quantity_unit, "print_quantity": line.print_quantity,
        "selected_for_print": line.selected_for_print, "workflow_state": line.workflow_state, "match_status": line.match_status,
        "match_method": line.match_method, "error_count": line.error_count, "issue_codes": issue_codes or [], "version": line.version,
        "address_profile_id": str(line.address_profile_id) if line.address_profile_id else None,
        "last_printed_at": line.last_printed_at, "successful_print_count": line.successful_print_count}


@router.get("/{consignment_id}/lines")
def list_lines(consignment_id: UUID, search: str | None = None, workflow_state: str | None = None, format_key: str | None = None,
    errors_only: bool = False, selected_only: bool = False, match_method: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), sort: str = "source_row", db: Session = Depends(get_db)):
    query = select(ConsignmentLine).where(ConsignmentLine.consignment_id == consignment_id)
    if workflow_state: query = query.where(ConsignmentLine.workflow_state == workflow_state)
    if format_key: query = query.where(ConsignmentLine.format_key == format_key)
    if errors_only: query = query.where(ConsignmentLine.error_count > 0)
    if selected_only: query = query.where(ConsignmentLine.selected_for_print.is_(True))
    if match_method: query = query.where(ConsignmentLine.match_method == match_method)
    if search:
        term = f"%{search.strip()}%"; query = query.where(or_(*[getattr(ConsignmentLine, field).ilike(term) for field in ("merchant_sku", "asin", "fnsku", "fsn", "listing_id", "title_snapshot")]))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    allowed_sort = {"source_row", "merchant_sku", "format_key", "print_quantity", "workflow_state"}
    rows = list(db.scalars(query.order_by(getattr(ConsignmentLine, sort if sort in allowed_sort else "source_row")).offset((page - 1) * page_size).limit(page_size)).all())
    issues = db.execute(select(ConsignmentIssue.consignment_line_id, ConsignmentIssue.code).where(ConsignmentIssue.consignment_line_id.in_([r.id for r in rows]), ConsignmentIssue.resolved.is_(False))).all() if rows else []
    by_line: dict[UUID, list[str]] = {}; [by_line.setdefault(line_id, []).append(code) for line_id, code in issues]
    return {"items": [_line_dict(row, by_line.get(row.id)) for row in rows], "total": total, "page": page, "page_size": page_size, "page_count": ceil(total / page_size) if total else 0}


@router.get("/{consignment_id}/printed")
def printed_lines(consignment_id: UUID, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    query = select(PrintJobLine, PrintJob).join(PrintJob).where(PrintJob.consignment_id == consignment_id, PrintJobLine.result == "success").order_by(PrintJobLine.completed_at.desc())
    rows = db.execute(query.offset((page - 1) * page_size).limit(page_size)).all()
    total = db.scalar(select(func.count(PrintJobLine.id)).join(PrintJob).where(PrintJob.consignment_id == consignment_id, PrintJobLine.result == "success")) or 0
    return {"items": [{"id": str(line.id), "job_id": str(job.id), "printed_at": line.completed_at, "copies": line.label_count, "status": line.status, "simulation": job.is_simulation, "snapshot": line.data_snapshot} for line, job in rows], "total": total, "page": page, "page_size": page_size}


@line_router.patch("/{line_id}")
def patch_line(line_id: UUID, payload: ConsignmentLinePatch, db: Session = Depends(get_db), principal:CurrentPrincipal=Depends(require_roles("Admin","Packing","Print Operator"))):
    line = db.scalar(select(ConsignmentLine).where(ConsignmentLine.id == line_id).options(selectinload(ConsignmentLine.product), selectinload(ConsignmentLine.consignment).selectinload(Consignment.account)))
    if not line: raise HTTPException(404, detail={"code": "CONSIGNMENT_LINE_NOT_FOUND", "message": "Line not found."})
    if line.version != payload.expected_version: raise HTTPException(409, detail={"code": "CONSIMENT_LINE_CHANGED", "message": "This row changed on another workstation. Refresh row."})
    direct = {"mrp_override", "net_quantity_value", "net_quantity_unit", "print_quantity", "format_key", "address_profile_id"}
    override = {"title": "title", "brand": "brand", "generic_name": "generic_name", "model_name": "model_name", "model_number": "model_number"}
    if payload.field not in direct | set(override): raise HTTPException(422, detail={"code": "FIELD_NOT_EDITABLE", "message": "This field cannot be edited here."})
    value = payload.value
    try:
        if payload.field == "mrp_override": value = Decimal(str(value)); assert value > 0
        if payload.field in {"net_quantity_value", "print_quantity"}: value = int(value); assert value >= 1
        if payload.field == "net_quantity_unit": assert str(value).strip()
    except (ValueError, InvalidOperation, AssertionError) as exc: raise HTTPException(422, detail={"code": "INVALID_FIELD_VALUE", "message": "Enter a valid positive value."}) from exc
    if payload.field in direct:
        old = getattr(line, payload.field); setattr(line, payload.field, value)
    else:
        values = dict(line.label_overrides or {}); old = values.get(override[payload.field]); values[override[payload.field]] = value; line.label_overrides = values
    line.version += 1
    ConsignmentValidationService(db).validate(line)
    audit_old = str(old) if isinstance(old, Decimal) else old
    audit_new = str(value) if isinstance(value, Decimal) else value
    actor_id=principal.id if isinstance(principal,CurrentPrincipal) else None
    db.add(AuditEvent(actor_id=actor_id,entity_type="consignment_line", entity_id=str(line.id), action="manual_override", changes={payload.field: {"old": audit_old, "new": audit_new}}, context={"consignment_line_id": str(line.id)})); db.commit()
    return _line_dict(line)


@line_router.post("/bulk-select")
def bulk_select(payload: BulkSelection, db: Session = Depends(get_db)):
    result = db.execute(update(ConsignmentLine).where(ConsignmentLine.consignment_id == payload.consignment_id, ConsignmentLine.id.in_(payload.line_ids)).values(selected_for_print=payload.selected, version=ConsignmentLine.version + 1))
    db.commit(); return {"updated": getattr(result, "rowcount", 0), "selected": payload.selected}


@line_router.post("/bulk-status")
def bulk_status(payload: BulkStatus, db: Session = Depends(get_db)):
    if payload.workflow_state not in {"to_print", "done", "excluded"}: raise HTTPException(422, detail={"code": "INVALID_WORKFLOW_STATE", "message": "Unsupported workflow state."})
    result = db.execute(update(ConsignmentLine).where(ConsignmentLine.consignment_id == payload.consignment_id, ConsignmentLine.id.in_(payload.line_ids)).values(workflow_state=payload.workflow_state, selected_for_print=False, version=ConsignmentLine.version + 1))
    db.commit(); return {"updated": getattr(result, "rowcount", 0), "workflow_state": payload.workflow_state}


@line_router.get("/{line_id}/resolved-label-data")
def resolved_label_data(line_id: UUID, db: Session = Depends(get_db)):
    line = db.scalar(select(ConsignmentLine).where(ConsignmentLine.id == line_id).options(selectinload(ConsignmentLine.product), selectinload(ConsignmentLine.consignment).selectinload(Consignment.account)))
    if not line: raise HTTPException(404, detail={"code": "CONSIGNMENT_LINE_NOT_FOUND", "message": "Line not found."})
    return ConsignmentLabelDataService(db).resolve(line)
