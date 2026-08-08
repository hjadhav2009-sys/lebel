from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories import ProductRepository
from app.models import CatalogImport, MarketplaceAccount
from app.schemas import ImportPreview, ImportSummary, ProductOut, ProductPage
from app.services.file_reader import parse_catalog
from app.services.import_service import CatalogImportService

router = APIRouter(prefix="/api/v1")


@router.get("/products", response_model=ProductPage)
def list_products(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), search: str | None = None, marketplace: str | None = None, account_id: UUID | None = None, category: str | None = None, image_status: str | None = None, db: Session = Depends(get_db)):
    items, total = ProductRepository(db).page(page=page, page_size=page_size, search=search, marketplace=marketplace, account_id=account_id, category=category, image_status=image_status)
    return ProductPage(items=[ProductOut.model_validate(item) for item in items], total=total, page=page, page_size=page_size)


@router.post("/imports/preview", response_model=list[ImportPreview])
async def preview_imports(marketplace: str = Form(...), files: list[UploadFile] = File(...)):
    previews = []
    for upload in files:
        try:
            parsed = parse_catalog(upload.filename or "upload", await upload.read(), marketplace.casefold())
            previews.append(ImportPreview(file=upload.filename or "upload", marketplace=marketplace, detected_type=parsed.detected_type, header_row=parsed.header_row, rows=len(parsed.rows), mapping_status="ready", warnings=[]))
        except ValueError as exc:
            previews.append(ImportPreview(file=upload.filename or "upload", marketplace=marketplace, detected_type="Unknown", header_row=0, rows=0, mapping_status="blocked", warnings=[str(exc)]))
    return previews


@router.post("/imports", response_model=list[ImportSummary])
async def run_imports(account_id: UUID = Form(...), files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    account = db.get(MarketplaceAccount, account_id)
    if account is None:
        raise HTTPException(404, "Marketplace account not found")
    summaries = []
    for upload in files:
        parsed = parse_catalog(upload.filename or "upload", await upload.read(), account.marketplace.value)
        catalog_import = CatalogImport(account_id=account.id, source_file=upload.filename or "upload", detected_type=parsed.detected_type)
        db.add(catalog_import)
        db.flush()
        CatalogImportService(db).apply(catalog_import, parsed.rows)
        summaries.append(ImportSummary(import_id=catalog_import.id, new=catalog_import.new_count, updated=catalog_import.updated_count, unchanged=catalog_import.unchanged_count, errors=catalog_import.error_count))
    return summaries
