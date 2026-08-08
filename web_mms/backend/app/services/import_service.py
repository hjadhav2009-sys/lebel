from dataclasses import asdict
from decimal import Decimal
from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, CatalogIdentifier, CatalogImport, CatalogImportRow, CatalogProduct, ImportError, ImportStatus, MarketplaceAccount, ProductImage, RowAction
from app.services.normalization import NormalizedProduct


class CatalogImportService:
    """Incremental, audit-first catalog upserts; never deletes absent products."""

    def __init__(self, session: Session):
        self.session = session

    def apply(self, catalog_import: CatalogImport, rows: Iterable[tuple[int, dict, NormalizedProduct]], actor_id: UUID | None = None) -> CatalogImport:
        catalog_import.status = ImportStatus.PROCESSING
        counts = {action: 0 for action in RowAction}
        for source_row, raw, normalized in rows:
            try:
                business_key = normalized.business_key()
                row_hash = normalized.row_hash()
                product = self.session.scalar(select(CatalogProduct).where(CatalogProduct.account_id == catalog_import.account_id, CatalogProduct.business_key == business_key))
                if product is None:
                    product = self._create_product(catalog_import, normalized, business_key, row_hash)
                    action = RowAction.NEW
                elif product.row_hash == row_hash:
                    action = RowAction.UNCHANGED
                else:
                    changes = self._update_product(product, catalog_import, normalized, row_hash)
                    self.session.add(AuditEvent(actor_id=actor_id, entity_type="catalog_product", entity_id=str(product.id), action="import_update", changes=changes, context={"import_id": str(catalog_import.id)}))
                    action = RowAction.UPDATED
                self.session.flush()
                self.session.add(CatalogImportRow(import_id=catalog_import.id, source_row=source_row, business_key=business_key, row_hash=row_hash, action=action, raw_row=raw, normalized_row=asdict(normalized), product_id=product.id))
            except ValueError as exc:
                action = RowAction.ERROR
                import_row = CatalogImportRow(import_id=catalog_import.id, source_row=source_row, action=action, raw_row=raw)
                self.session.add(import_row)
                self.session.flush()
                account = self.session.get(MarketplaceAccount, catalog_import.account_id)
                self.session.add(ImportError(import_id=catalog_import.id, import_row_id=import_row.id, severity="blocking", marketplace=account.marketplace.value if account else "unknown", account=account.name if account else None, source_file=catalog_import.source_file, source_row=source_row, product_identifier=normalized.sku, field="identifier", code="invalid_business_key", message=str(exc), suggested_action="Provide a unique SKU, FSN, ASIN, or Listing ID and import again."))
            counts[action] += 1
        catalog_import.total_rows = sum(counts.values())
        catalog_import.new_count, catalog_import.updated_count = counts[RowAction.NEW], counts[RowAction.UPDATED]
        catalog_import.unchanged_count, catalog_import.error_count = counts[RowAction.UNCHANGED], counts[RowAction.ERROR]
        catalog_import.status = ImportStatus.COMPLETED
        self.session.commit()
        return catalog_import

    def _create_product(self, imp: CatalogImport, row: NormalizedProduct, business_key: str, row_hash: str) -> CatalogProduct:
        product = CatalogProduct(account_id=imp.account_id, business_key=business_key, row_hash=row_hash, sku=row.sku, title=row.title, brand=row.brand, mrp=Decimal(row.mrp) if row.mrp else None, category=row.category, source_file=imp.source_file, source_template=row.source_template, source_category=row.source_category, extra_attributes=row.extra_attributes, last_import_id=imp.id)
        product.identifiers = [CatalogIdentifier(kind=k, value=v) for k, v in row.identifiers.items()]
        product.images = [ProductImage(url=url, kind="main" if i == 0 else "other", position=i) for i, url in enumerate(row.images)]
        self.session.add(product)
        return product

    def _update_product(self, product: CatalogProduct, imp: CatalogImport, row: NormalizedProduct, row_hash: str) -> dict:
        changes = {}
        values = {"sku": row.sku, "title": row.title, "brand": row.brand, "mrp": Decimal(row.mrp) if row.mrp else None, "category": row.category, "extra_attributes": row.extra_attributes}
        for field, new_value in values.items():
            old_value = getattr(product, field)
            if old_value != new_value:
                changes[field] = {"old": str(old_value) if old_value is not None else None, "new": str(new_value) if new_value is not None else None}
                setattr(product, field, new_value)
        product.row_hash, product.source_file, product.last_import_id = row_hash, imp.source_file, imp.id
        return changes
