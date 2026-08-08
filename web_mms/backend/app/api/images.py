from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import AuditEvent, CatalogProduct

router = APIRouter(prefix="/images", tags=["images"])

@router.post("/products/{product_id}/enrichment", status_code=202)
def request_enrichment(product_id: UUID, db: Session = Depends(get_db)):
    product = db.get(CatalogProduct, product_id)
    if not product: raise HTTPException(404, "Product not found")
    db.add(AuditEvent(entity_type="catalog_product", entity_id=str(product_id), action="image_enrichment_requested", changes={}, context={"status": "pending"}))
    db.commit()
    return {"status": "pending", "product_id": str(product_id)}
