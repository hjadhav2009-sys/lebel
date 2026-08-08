from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import AuditEvent, Consignment, ConsignmentIssue, ImportError, Marketplace

router = APIRouter(prefix="/errors", tags=["errors"])


@router.get("")
def list_errors(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), severity: str | None = None,
    marketplace: str | None = None, code: str | None = None, resolved: bool | None = None, source_type: str = "all", db: Session = Depends(get_db)):
    items = []
    if source_type in {"all", "import"}:
        filters = []
        if severity: filters.append(ImportError.severity == severity)
        if marketplace: filters.append(ImportError.marketplace == marketplace)
        if code: filters.append(ImportError.code == code)
        if resolved is not None: filters.append(ImportError.resolved == resolved)
        rows = db.scalars(select(ImportError).where(*filters).order_by(ImportError.created_at.desc())).all()
        items.extend({"id": str(row.id), "created_at": row.created_at, "source_type": "import", "severity": row.severity,
            "marketplace": row.marketplace, "account": row.account, "source_file": row.source_file, "source_row": row.source_row,
            "product_identifier": row.product_identifier, "field": row.field, "code": row.code, "message": row.message,
            "suggested_action": row.suggested_action, "resolved": row.resolved} for row in rows)
    if source_type in {"all", "consignment"}:
        filters = []
        if severity: filters.append(ConsignmentIssue.severity == severity)
        if code: filters.append(ConsignmentIssue.code == code)
        if resolved is not None: filters.append(ConsignmentIssue.resolved == resolved)
        query = select(ConsignmentIssue, Consignment).join(Consignment)
        if marketplace: query = query.where(Consignment.marketplace == Marketplace(marketplace.casefold()))
        rows = db.execute(query.where(*filters).order_by(ConsignmentIssue.created_at.desc())).all()
        items.extend({"id": str(row.id), "created_at": row.created_at, "source_type": "consignment", "severity": row.severity,
            "marketplace": consignment.marketplace.value, "account": None, "source_file": consignment.source_file_name, "source_row": None,
            "product_identifier": str(row.consignment_line_id) if row.consignment_line_id else None, "field": row.field, "code": row.code,
            "message": row.message, "suggested_action": "Open the consignment line and correct the field.", "resolved": row.resolved} for row, consignment in rows)
    items.sort(key=lambda item: item["created_at"], reverse=True)
    total = len(items); start = (page - 1) * page_size
    return {"items": items[start:start + page_size], "total": total, "page": page, "page_size": page_size}


@router.post("/{error_id}/resolve")
def resolve_error(error_id: UUID, source_type: str = "import", db: Session = Depends(get_db)):
    item = db.get(ConsignmentIssue if source_type == "consignment" else ImportError, error_id)
    if not item: raise HTTPException(404, detail={"code": "ERROR_NOT_FOUND", "message": "Error not found."})
    item.resolved = True
    db.add(AuditEvent(entity_type=f"{source_type}_error", entity_id=str(item.id), action="resolved", changes={"resolved": {"old": False, "new": True}}, context={}))
    db.commit(); return {"status": "resolved"}
