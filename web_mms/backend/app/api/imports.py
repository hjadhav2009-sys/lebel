from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import CatalogBatch, CatalogImport, ImportError, MarketplaceAccount
from app.schemas import ImportPreview, ImportSummary
from app.services.file_reader import parse_catalog
from app.services.import_service import CatalogImportService

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/preview", response_model=list[ImportPreview])
async def preview_imports(marketplace: str = Form(...), account_id: UUID | None = Form(None), files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    previews = []
    for upload in files:
        filename, payload = upload.filename or "upload", await upload.read()
        try:
            parsed = parse_catalog(filename, payload, marketplace.casefold())
            previous = bool(db.scalar(select(CatalogImport.id).where(CatalogImport.file_sha256 == parsed.file_sha256, CatalogImport.account_id == account_id).limit(1))) if account_id else False
            previews.append(ImportPreview(file=filename, sheet=parsed.sheet_name, marketplace=marketplace, detected_type=parsed.detected_type, header_row=parsed.header_row, rows=len(parsed.rows), mapping_status="warning" if parsed.warnings else "ready", warnings=parsed.warnings, file_sha256=parsed.file_sha256, previously_imported=previous))
        except ValueError as exc:
            previews.append(ImportPreview(file=filename, sheet="—", marketplace=marketplace, detected_type="Unknown", header_row=0, rows=0, mapping_status="blocked", warnings=[str(exc)], file_sha256=""))
    return previews


@router.post("", response_model=list[ImportSummary])
async def run_imports(account_id: UUID = Form(...), batch_id: UUID | None = Form(None), files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    account = db.get(MarketplaceAccount, account_id)
    if not account: raise HTTPException(404, "Marketplace account not found")
    summaries = []
    for upload in files:
        filename, payload = upload.filename or "upload", await upload.read()
        parsed = parse_catalog(filename, payload, account.marketplace.value)
        item = CatalogImport(batch_id=batch_id, account_id=account.id, source_file=filename, original_filename=filename, sheet_name=parsed.sheet_name, file_sha256=parsed.file_sha256, file_size=parsed.file_size, mapping={"header_row": parsed.header_row}, detected_type=parsed.detected_type)
        db.add(item); db.flush()
        for warning in parsed.warnings:
            db.add(ImportError(import_id=item.id, severity="blocking", marketplace=account.marketplace.value, account=account.name, source_file=filename, code="FORMULA_RESULT_MISSING", message=warning, suggested_action="Open and recalculate the workbook in Excel, save it, then import again."))
        item.error_count = len(parsed.warnings)
        CatalogImportService(db).apply(item, parsed.rows)
        summaries.append(ImportSummary(import_id=item.id, new=item.new_count, updated=item.updated_count, unchanged=item.unchanged_count, errors=item.error_count))
    return summaries


@router.get("")
def import_history(db: Session = Depends(get_db)):
    rows = db.scalars(select(CatalogImport).order_by(CatalogImport.created_at.desc()).limit(200)).all()
    return [{"id": str(item.id), "date": item.created_at, "account_id": str(item.account_id), "source_file": item.original_filename, "sheet": item.sheet_name, "rows": item.total_rows, "new": item.new_count, "updated": item.updated_count, "unchanged": item.unchanged_count, "errors": item.error_count, "status": item.status.value} for item in rows]


@router.post("/batches", status_code=201)
def create_batch(account_id: UUID, name: str, db: Session = Depends(get_db)):
    account = db.get(MarketplaceAccount, account_id)
    if not account: raise HTTPException(404, "Marketplace account not found")
    batch = CatalogBatch(account_id=account.id, marketplace=account.marketplace, name=name)
    db.add(batch); db.commit(); db.refresh(batch)
    return {"id": str(batch.id), "name": batch.name, "status": batch.status}


@router.post("/batches/{batch_id}/complete")
def complete_batch(batch_id: UUID, db: Session = Depends(get_db)):
    batch = db.get(CatalogBatch, batch_id)
    if not batch: raise HTTPException(404, "Catalog batch not found")
    batch.status, batch.completed_at = "completed", datetime.now(timezone.utc)
    db.commit()
    return {"status": batch.status}
