from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class IdentifierOut(BaseModel):
    kind: str
    value: str
    model_config = ConfigDict(from_attributes=True)


class ImageOut(BaseModel):
    id: UUID
    url: str
    kind: str
    position: int
    source: str
    status: str
    model_config = ConfigDict(from_attributes=True)


class MarketplaceAccountOut(BaseModel):
    id: UUID
    marketplace: str
    name: str
    model_config = ConfigDict(from_attributes=True)


class ProductOut(BaseModel):
    id: UUID
    sku: str | None
    title: str | None
    brand: str | None
    mrp: Decimal | None
    category: str | None
    source_file: str | None
    source_template: str | None
    updated_at: datetime
    identifiers: list[IdentifierOut]
    images: list[ImageOut]
    account: MarketplaceAccountOut
    model_config = ConfigDict(from_attributes=True)


class ProductPage(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    page_size: int


class ImportSummary(BaseModel):
    import_id: UUID
    new: int
    updated: int
    unchanged: int
    errors: int


class ImportPreview(BaseModel):
    file: str
    marketplace: str
    detected_type: str
    header_row: int
    rows: int
    mapping_status: str
    warnings: list[str]
