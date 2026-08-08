from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import CatalogIdentifier, CatalogProduct, MarketplaceAccount


class ProductRepository:
    def __init__(self, session: Session):
        self.session = session

    def page(self, *, page: int, page_size: int, search: str | None = None, marketplace: str | None = None, account_id: UUID | None = None, category: str | None = None, image_status: str | None = None):
        filters = []
        if account_id:
            filters.append(CatalogProduct.account_id == account_id)
        if marketplace:
            filters.append(CatalogProduct.account.has(MarketplaceAccount.marketplace == marketplace))
        if category:
            filters.append(CatalogProduct.category == category)
        if image_status == "available":
            filters.append(CatalogProduct.images.any())
        elif image_status == "missing":
            filters.append(~CatalogProduct.images.any())
        if search:
            term = f"%{search.strip()}%"
            filters.append(or_(CatalogProduct.sku.ilike(term), CatalogProduct.title.ilike(term), CatalogProduct.identifiers.any(CatalogIdentifier.value.ilike(term))))
        total = self.session.scalar(select(func.count()).select_from(CatalogProduct).where(*filters)) or 0
        query = select(CatalogProduct).options(selectinload(CatalogProduct.identifiers), selectinload(CatalogProduct.images), selectinload(CatalogProduct.account)).where(*filters).order_by(CatalogProduct.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
        return list(self.session.scalars(query).all()), total
