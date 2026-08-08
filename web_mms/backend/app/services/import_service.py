from dataclasses import asdict
from decimal import Decimal
from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import DataError, IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import AuditEvent, CatalogIdentifier, CatalogImport, CatalogImportRow, CatalogProduct, ImportError, ImportStatus, MarketplaceAccount, ProductImage, RowAction
from app.services.normalization import NormalizedProduct


class CatalogImportService:
    """Incremental, audit-first catalog upserts; never deletes absent products."""

    def __init__(self, session: Session):
        self.session = session

    def apply(self, catalog_import: CatalogImport, rows: Iterable[tuple[int, dict, NormalizedProduct]], actor_id: UUID | None = None) -> CatalogImport:
        catalog_import.status = ImportStatus.PROCESSING
        preflight_errors = catalog_import.error_count or 0
        counts = {action: 0 for action in RowAction}
        for source_row, raw, normalized in rows:
            try:
                with self.session.begin_nested():
                    business_key = normalized.business_key()
                    row_hash = normalized.row_hash()
                    product = self.session.scalar(select(CatalogProduct).where(CatalogProduct.account_id == catalog_import.account_id, CatalogProduct.business_key == business_key))
                    source_key = normalized.source_template or catalog_import.source_file
                    if product is None:
                        product = self._create_product(catalog_import, normalized, business_key, row_hash)
                        action = RowAction.NEW
                    elif (product.extra_attributes or {}).get("_source_hashes", {}).get(source_key) == row_hash:
                        action = RowAction.UNCHANGED
                    else:
                        changes = self._update_product(product, catalog_import, normalized, row_hash)
                        self.session.add(AuditEvent(actor_id=actor_id, entity_type="catalog_product", entity_id=str(product.id), action="import_update", changes=changes, context={"import_id": str(catalog_import.id), "source": source_key}))
                        action = RowAction.UPDATED
                    self.session.flush()
                    self.session.add(CatalogImportRow(import_id=catalog_import.id, source_row=source_row, business_key=business_key, row_hash=row_hash, action=action, raw_row=raw, normalized_row=asdict(normalized), product_id=product.id))
            except (ValueError, IntegrityError, DataError, SQLAlchemyError) as exc:
                action = RowAction.ERROR
                self._record_error(catalog_import, source_row, raw, normalized, exc, "row_validation_failed")
            except Exception as exc:  # row isolation is intentional; catastrophic setup errors are handled outside this loop
                action = RowAction.ERROR
                self._record_error(catalog_import, source_row, raw, normalized, exc, "unexpected_row_error")
            counts[action] += 1
        catalog_import.total_rows = sum(counts.values())
        catalog_import.new_count, catalog_import.updated_count = counts[RowAction.NEW], counts[RowAction.UPDATED]
        catalog_import.unchanged_count, catalog_import.error_count = counts[RowAction.UNCHANGED], counts[RowAction.ERROR] + preflight_errors
        catalog_import.status = ImportStatus.COMPLETED_WITH_ERRORS if catalog_import.error_count else ImportStatus.COMPLETED
        self.session.commit()
        return catalog_import

    def _create_product(self, imp: CatalogImport, row: NormalizedProduct, business_key: str, row_hash: str) -> CatalogProduct:
        source_key = row.source_template or imp.source_file
        attributes = dict(row.extra_attributes)
        attributes["_source_hashes"] = {source_key: row_hash}
        product = CatalogProduct(account_id=imp.account_id, business_key=business_key, row_hash=row_hash, sku=row.sku, title=row.title, brand=row.brand, mrp=Decimal(row.mrp) if row.mrp else None, category=row.category, source_file=imp.source_file, source_template=row.source_template, source_category=row.source_category, extra_attributes=attributes, last_import_id=imp.id)
        product.identifiers = [CatalogIdentifier(kind=k, value=v, authoritative_source=source_key) for k, v in row.identifiers.items()]
        product.images = [ProductImage(url=url, kind="main" if i == 0 else "other", position=i, source="import", source_reference=source_key) for i, url in enumerate(row.images)]
        self.session.add(product)
        return product

    def _update_product(self, product: CatalogProduct, imp: CatalogImport, row: NormalizedProduct, row_hash: str) -> dict:
        changes = {}
        source_key = row.source_template or imp.source_file
        merged_attributes = {k: v for k, v in (product.extra_attributes or {}).items() if k != "_source_hashes"}
        merged_attributes.update(row.extra_attributes)
        source_hashes = dict((product.extra_attributes or {}).get("_source_hashes", {}))
        source_hashes[source_key] = row_hash
        merged_attributes["_source_hashes"] = source_hashes
        values = {"sku": row.sku, "title": row.title, "brand": row.brand, "mrp": Decimal(row.mrp) if row.mrp else None, "category": row.category, "extra_attributes": merged_attributes, "source_template": row.source_template, "source_category": row.source_category}
        for field, new_value in values.items():
            if new_value is None and field in {"sku", "title", "brand", "mrp", "category", "source_template", "source_category"}:
                continue
            old_value = getattr(product, field)
            if old_value != new_value:
                changes[field] = {"old": str(old_value) if old_value is not None else None, "new": str(new_value) if new_value is not None else None}
                setattr(product, field, new_value)
        existing_identifiers = {(item.kind, item.value.casefold()): item for item in product.identifiers}
        for kind, value in row.identifiers.items():
            key = (kind, value.casefold())
            if key not in existing_identifiers:
                product.identifiers.append(CatalogIdentifier(kind=kind, value=value, authoritative_source=source_key))
                changes.setdefault("identifiers", {"added": []})["added"].append({"kind": kind, "value": value})
        incoming_urls = set(row.images)
        existing_urls = {image.url: image for image in product.images}
        for position, url in enumerate(row.images):
            if url in existing_urls:
                image = existing_urls[url]
                image.kind, image.position, image.status = ("main" if position == 0 else "other"), position, "available"
            else:
                product.images.append(ProductImage(url=url, kind="main" if position == 0 else "other", position=position, source="import", source_reference=source_key))
                changes.setdefault("images", {"added": [], "stale": []})["added"].append(url)
        for image in product.images:
            if image.source == "import" and image.source_reference == source_key and image.url not in incoming_urls:
                image.status = "stale"
                changes.setdefault("images", {"added": [], "stale": []})["stale"].append(image.url)
        product.row_hash, product.source_file, product.last_import_id = row_hash, imp.source_file, imp.id
        return changes

    def _record_error(self, catalog_import, source_row, raw, normalized, exc, code):
        with self.session.begin_nested():
            import_row = CatalogImportRow(import_id=catalog_import.id, source_row=source_row, action=RowAction.ERROR, raw_row=raw)
            self.session.add(import_row)
            self.session.flush()
            account = self.session.get(MarketplaceAccount, catalog_import.account_id)
            self.session.add(ImportError(import_id=catalog_import.id, import_row_id=import_row.id, severity="blocking", marketplace=account.marketplace.value if account else "unknown", account=account.name if account else None, source_file=catalog_import.source_file, source_row=source_row, product_identifier=normalized.sku, field=None, code=code, message=str(exc), suggested_action="Correct the source row and import again."))
