from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class APIError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class IdentifierOut(BaseModel):
    kind: str
    value: str
    source: str
    model_config = ConfigDict(from_attributes=True)


class ImageOut(BaseModel):
    id: UUID
    url: str
    cached_url: str | None
    kind: str
    position: int
    source: str
    status: str
    last_checked_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class MarketplaceAccountOut(BaseModel):
    id: UUID
    marketplace: str
    name: str
    external_id: str | None
    default_address_profile_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AccountCreate(BaseModel):
    marketplace: str
    name: str = Field(min_length=2, max_length=120)
    external_id: str | None = None
    default_address_profile_id: UUID | None = None
    is_active: bool = True


class ProductOut(BaseModel):
    id: UUID
    sku: str | None
    title: str | None
    brand: str | None
    mrp: Decimal | None
    category: str | None
    source_file: str | None
    source_template: str | None
    source_category: str | None
    extra_attributes: dict[str, Any]
    created_at: datetime
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
    page_count: int


class InventoryStats(BaseModel):
    total: int
    with_images: int
    missing_images: int


class AuditEventOut(BaseModel):
    id: UUID
    created_at: datetime
    action: str
    changes: dict[str, Any]
    context: dict[str, Any]
    actor_id: UUID | None
    model_config = ConfigDict(from_attributes=True)


class ImportSummary(BaseModel):
    import_id: UUID
    new: int
    updated: int
    unchanged: int
    errors: int


class ImportPreview(BaseModel):
    file: str
    sheet: str
    marketplace: str
    detected_type: str
    header_row: int
    rows: int
    mapping_status: str
    warnings: list[str]
    file_sha256: str
    previously_imported: bool = False


class CurrentUserOut(BaseModel):
    id: UUID | None
    email: str
    display_name: str
    roles: list[str]
    development: bool = False


class ErrorOut(BaseModel):
    id: UUID
    created_at: datetime
    severity: str
    marketplace: str
    account: str | None
    source_file: str | None
    source_row: int | None
    product_identifier: str | None
    field: str | None
    code: str
    message: str
    suggested_action: str | None
    resolved: bool
    model_config = ConfigDict(from_attributes=True)


class ErrorPage(BaseModel):
    items: list[ErrorOut]
    total: int
    page: int
    page_size: int
