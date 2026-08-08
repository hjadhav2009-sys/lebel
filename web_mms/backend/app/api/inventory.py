from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import AuditEvent, PrintJob, PrintJobLine
from app.repositories import ProductRepository
from app.schemas import AuditEventOut, InventoryStats, ProductOut, ProductPage

router = APIRouter(prefix="/products", tags=["inventory"])


@router.get("", response_model=ProductPage)
def list_products(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), search: str | None = None, marketplace: str | None = None, account_id: UUID | None = None, category: str | None = None, image_status: str | None = None, sort: str = "updated_at", sort_direction: str = Query("desc", pattern="^(asc|desc)$"), db: Session = Depends(get_db)):
    items, total, page_count = ProductRepository(db).page(page=page, page_size=page_size, search=search, marketplace=marketplace, account_id=account_id, category=category, image_status=image_status, sort=sort, sort_direction=sort_direction)
    return ProductPage(items=[ProductOut.model_validate(item) for item in items], total=total, page=page, page_size=page_size, page_count=page_count)


@router.get("/stats", response_model=InventoryStats)
def inventory_stats(marketplace: str | None = None, account_id: UUID | None = None, db: Session = Depends(get_db)):
    total, with_images = ProductRepository(db).stats(marketplace, account_id)
    return InventoryStats(total=total, with_images=with_images, missing_images=total - with_images)


@router.get("/{product_id}", response_model=ProductOut)
def product_detail(product_id: UUID, db: Session = Depends(get_db)):
    product = ProductRepository(db).get(product_id)
    if not product:
        raise HTTPException(404, detail={"code": "product_not_found", "message": "Product not found", "details": {"product_id": str(product_id)}})
    return ProductOut.model_validate(product)


@router.get("/{product_id}/audit", response_model=list[AuditEventOut])
def product_audit(product_id: UUID, db: Session = Depends(get_db)):
    return list(db.scalars(select(AuditEvent).where(AuditEvent.entity_type == "catalog_product", AuditEvent.entity_id == str(product_id)).order_by(AuditEvent.created_at.desc())).all())


@router.get("/{product_id}/print-history")
def print_history(product_id: UUID, db: Session = Depends(get_db)):
    query = select(PrintJobLine, PrintJob).join(PrintJob, PrintJob.id == PrintJobLine.print_job_id).where(PrintJobLine.data_snapshot["product_id"].as_string() == str(product_id)).order_by(PrintJob.created_at.desc())
    return [{"job_id": str(job.id), "printed_at": job.updated_at, "printer": job.printer_name, "copies": line.label_count, "renderer_version": job.renderer_version, "result": job.status} for line, job in db.execute(query).all()]


@router.patch("/{product_id}/label-data")
def update_label_data(product_id: UUID, payload: dict, mode: str = Query("catalog", pattern="^(catalog|consignment)$"), db: Session = Depends(get_db)):
    product = ProductRepository(db).get(product_id)
    if not product: raise HTTPException(404, "Product not found")
    fields = payload.get("fields", {})
    if mode == "consignment":
        return {"mode": mode, "fields": fields, "persisted": False}
    changes = {}
    for field in ("brand", "mrp", "category"):
        if field in fields and fields[field] != getattr(product, field):
            changes[field] = {"old": str(getattr(product, field)) if getattr(product, field) is not None else None, "new": str(fields[field])}
            setattr(product, field, fields[field])
    extra = dict(product.extra_attributes or {})
    for field in ("model_name", "model_number", "color", "net_quantity", "generic_name", "address_profile_id"):
        if field in fields and extra.get(field) != fields[field]:
            changes[field] = {"old": extra.get(field), "new": fields[field]}
            extra[field] = fields[field]
    product.extra_attributes = extra
    db.add(AuditEvent(entity_type="catalog_product", entity_id=str(product.id), action="manual_label_data_update", changes=changes, context={"mode": mode}))
    db.commit()
    return {"mode": mode, "persisted": True, "changes": changes}
