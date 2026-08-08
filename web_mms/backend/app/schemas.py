from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
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


class ConsignmentCreate(BaseModel):
    account_id: UUID
    marketplace: str
    name: str = Field(min_length=2, max_length=180)
    reference_number: str | None = None


class ConsignmentPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    reference_number: str | None = None
    status: str | None = None


class ConsignmentLinePatch(BaseModel):
    expected_version: int
    field: str
    value: Any


class BulkSelection(BaseModel):
    consignment_id: UUID
    line_ids: list[UUID]
    selected: bool


class BulkStatus(BaseModel):
    consignment_id: UUID
    line_ids: list[UUID]
    workflow_state: str


class AddressProfileWrite(BaseModel):
    account_id: UUID
    name: str = Field(min_length=2, max_length=120)
    marketed_by: str = Field(min_length=1)
    address_line_1: str = Field(min_length=1)
    address_line_2: str | None = None
    city_state: str = Field(min_length=1)
    email: str | None = None
    phone: str | None = None
    origin: str | None = None
    is_active: bool = True
    is_default: bool = False


class LabelFormatWrite(BaseModel):
    account_id: UUID | None = None
    key: str = Field(pattern=r"^[a-z0-9_]+$")
    display_name: str
    marketplace: str | None = None
    generic_name: str | None = None
    required_fields: list[str] = Field(default_factory=list)
    field_order: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class PrintJobCreate(BaseModel):
    consignment_id: UUID
    line_ids: list[UUID] | None = None
    printer_profile_id: UUID | None = None
    test_labels: bool = False


class ReprintRequest(BaseModel):
    source_line_ids: list[UUID] | None = None


class AgentPairRequest(BaseModel):
    code: str
    machine_name: str = Field(min_length=1, max_length=180)
    name: str = Field(min_length=1, max_length=120)
    version: str | None = None


class AgentHeartbeat(BaseModel):
    version: str | None = None
    windows_version: str | None = None
    uptime_seconds: int | None = Field(default=None, ge=0)
    last_error: str | None = None


class DiscoveredPrinter(BaseModel):
    name: str
    driver_name: str = "Unknown"
    port_name: str | None = None
    dpi: int = Field(default=203, ge=100, le=1200)
    status: str = "online"
    is_default: bool = False
    is_network: bool = False


class PrinterSync(BaseModel):
    printers: list[DiscoveredPrinter]


class AgentJobReport(BaseModel):
    claim_token: str
    status: str
    spool_job_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class PrinterProfileWrite(BaseModel):
    marketplace: Literal["amazon", "flipkart"]
    account_id: UUID | None = None
    media_width_mm: float = Field(gt=0, le=300)
    media_height_mm: float = Field(gt=0, le=300)
    gap_mm: float = Field(default=2, ge=0, le=30)
    speed: int | None = Field(default=None, ge=1, le=15)
    darkness: int | None = Field(default=None, ge=0, le=15)
    renderer: str
    config: dict[str, Any] = Field(default_factory=dict)


class RendererApprovalWrite(BaseModel):
    test_print_job_id: UUID
    format_key: str | None = None
    notes: str | None = None


class BarcodeVerificationWrite(BaseModel):
    print_job_line_id: UUID | None = None
    expected_value: str
    scanned_value: str
