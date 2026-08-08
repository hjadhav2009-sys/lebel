import math
from uuid import UUID

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import CatalogIdentifier, CatalogProduct, MarketplaceAccount, ProductImage


SORT_COLUMNS = {
    "sku": CatalogProduct.sku,
    "title": CatalogProduct.title,
    "brand": CatalogProduct.brand,
    "mrp": CatalogProduct.mrp,
    "category": CatalogProduct.category,
    "updated_at": CatalogProduct.updated_at,
}


class ProductRepository:
    def __init__(self, session: Session):
        self.session = session

    def _filters(self, search=None, marketplace=None, account_id=None, category=None, image_status=None):
        filters = []
        if account_id:
            filters.append(CatalogProduct.account_id == account_id)
        if marketplace:
            filters.append(CatalogProduct.account.has(MarketplaceAccount.marketplace == marketplace))
        if category:
            filters.append(CatalogProduct.category == category)
        if image_status == "available":
            filters.append(CatalogProduct.images.any(ProductImage.status == "available"))
        elif image_status == "missing":
            filters.append(~CatalogProduct.images.any(ProductImage.status == "available"))
        if search:
            term = f"%{search.strip()}%"
            filters.append(or_(CatalogProduct.sku.ilike(term), CatalogProduct.title.ilike(term), CatalogProduct.brand.ilike(term), CatalogProduct.identifiers.any(CatalogIdentifier.value.ilike(term))))
        return filters

    def page(self, *, page: int, page_size: int, search=None, marketplace=None, account_id: UUID | None = None, category=None, image_status=None, sort="updated_at", sort_direction="desc"):
        filters = self._filters(search, marketplace, account_id, category, image_status)
        total = self.session.scalar(select(func.count()).select_from(CatalogProduct).where(*filters)) or 0
        column = SORT_COLUMNS.get(sort, CatalogProduct.updated_at)
        order = desc(column) if sort_direction == "desc" else asc(column)
        query = select(CatalogProduct).options(selectinload(CatalogProduct.identifiers), selectinload(CatalogProduct.images), selectinload(CatalogProduct.account)).where(*filters).order_by(order.nullslast(), CatalogProduct.id).offset((page - 1) * page_size).limit(page_size)
        return list(self.session.scalars(query).all()), total, math.ceil(total / page_size) if total else 0

    def get(self, product_id: UUID):
        query = select(CatalogProduct).options(selectinload(CatalogProduct.identifiers), selectinload(CatalogProduct.images), selectinload(CatalogProduct.account)).where(CatalogProduct.id == product_id)
        return self.session.scalar(query)

    def stats(self, marketplace=None, account_id=None):
        filters = self._filters(marketplace=marketplace, account_id=account_id)
        total = self.session.scalar(select(func.count()).select_from(CatalogProduct).where(*filters)) or 0
        with_images = self.session.scalar(select(func.count()).select_from(CatalogProduct).where(*filters, CatalogProduct.images.any(ProductImage.status == "available"))) or 0
        return total, with_images
