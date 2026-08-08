import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Marketplace(str, enum.Enum):
    AMAZON = "amazon"
    FLIPKART = "flipkart"


class ImportStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class RowAction(str, enum.Enum):
    NEW = "new"
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    ERROR = "error"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    roles: Mapped[list[Role]] = relationship(secondary="user_roles")


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)


class MarketplaceAccount(TimestampMixin, Base):
    __tablename__ = "marketplace_accounts"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    marketplace: Mapped[Marketplace] = mapped_column(Enum(Marketplace, name="marketplace"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    external_id: Mapped[str | None] = mapped_column(String(120))
    default_address_profile_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("address_profiles.id", use_alter=True, name="fk_account_default_address"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("marketplace", "name"),)


class CatalogProduct(TimestampMixin, Base):
    __tablename__ = "catalog_products"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("marketplace_accounts.id"), index=True)
    business_key: Mapped[str] = mapped_column(String(320))
    row_hash: Mapped[str] = mapped_column(String(64), index=True)
    sku: Mapped[str | None] = mapped_column(String(180), index=True)
    title: Mapped[str | None] = mapped_column(Text)
    brand: Mapped[str | None] = mapped_column(String(180))
    mrp: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    category: Mapped[str | None] = mapped_column(String(180), index=True)
    source_file: Mapped[str | None] = mapped_column(String(255))
    source_template: Mapped[str | None] = mapped_column(String(120))
    source_category: Mapped[str | None] = mapped_column(String(180))
    extra_attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    last_import_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("catalog_imports.id", use_alter=True))
    account: Mapped[MarketplaceAccount] = relationship()
    identifiers: Mapped[list["CatalogIdentifier"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    images: Mapped[list["ProductImage"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    __table_args__ = (
        UniqueConstraint("account_id", "business_key"),
        Index("ix_catalog_search", "account_id", "sku", "category"),
        Index("ix_catalog_products_updated_at", "updated_at"),
    )


class CatalogIdentifier(Base):
    __tablename__ = "catalog_identifiers"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalog_products.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    value: Mapped[str] = mapped_column(String(180), index=True)
    product: Mapped[CatalogProduct] = relationship(back_populates="identifiers")
    source: Mapped[str] = mapped_column(String(40), default="import")
    authoritative_source: Mapped[str | None] = mapped_column(String(120))
    __table_args__ = (
        UniqueConstraint("product_id", "kind", "value"),
        Index("ix_catalog_identifiers_kind_value", "kind", "value"),
    )


class ProductImage(Base):
    __tablename__ = "product_images"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalog_products.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(Text)
    cached_url: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(30), default="other")
    position: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(40), default="import")
    source_reference: Mapped[str | None] = mapped_column(String(180))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="available")
    product: Mapped[CatalogProduct] = relationship(back_populates="images")
    __table_args__ = (UniqueConstraint("product_id", "url"),)


class CatalogImport(TimestampMixin, Base):
    __tablename__ = "catalog_imports"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("catalog_batches.id"), index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("marketplace_accounts.id"), index=True)
    source_file: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    sheet_name: Mapped[str | None] = mapped_column(String(255))
    file_sha256: Mapped[str] = mapped_column(String(64), index=True)
    file_size: Mapped[int] = mapped_column(Integer)
    mapping: Mapped[dict] = mapped_column(JSON, default=dict)
    detected_type: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[ImportStatus] = mapped_column(Enum(ImportStatus, name="import_status"), default=ImportStatus.PENDING)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    new_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    unchanged_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class CatalogImportRow(Base):
    __tablename__ = "catalog_import_rows"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    import_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalog_imports.id", ondelete="CASCADE"), index=True)
    source_row: Mapped[int] = mapped_column(Integer)
    business_key: Mapped[str | None] = mapped_column(String(320))
    row_hash: Mapped[str | None] = mapped_column(String(64))
    action: Mapped[RowAction] = mapped_column(Enum(RowAction, name="row_action"))
    raw_row: Mapped[dict] = mapped_column(JSON)
    normalized_row: Mapped[dict | None] = mapped_column(JSON)
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("catalog_products.id"))
    __table_args__ = (UniqueConstraint("import_id", "source_row"),)


class ImportError(Base):
    __tablename__ = "import_errors"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    import_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("catalog_imports.id"), index=True)
    import_row_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("catalog_import_rows.id"))
    severity: Mapped[str] = mapped_column(String(20), index=True)
    marketplace: Mapped[str] = mapped_column(String(30))
    account: Mapped[str | None] = mapped_column(String(120))
    source_file: Mapped[str | None] = mapped_column(String(255))
    source_row: Mapped[int | None] = mapped_column(Integer)
    product_identifier: Mapped[str | None] = mapped_column(String(180))
    field: Mapped[str | None] = mapped_column(String(80))
    code: Mapped[str] = mapped_column(String(80))
    message: Mapped[str] = mapped_column(Text)
    suggested_action: Mapped[str | None] = mapped_column(Text)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        Index("ix_import_errors_code_resolved", "code", "resolved"),
        Index("ix_import_errors_import_id_source_row", "import_id", "source_row"),
    )


class CatalogBatch(Base):
    __tablename__ = "catalog_batches"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("marketplace_accounts.id"), index=True)
    marketplace: Mapped[Marketplace] = mapped_column(Enum(Marketplace, name="marketplace"))
    name: Mapped[str] = mapped_column(String(180))
    status: Mapped[str] = mapped_column(String(30), default="pending")
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Consignment(TimestampMixin, Base):
    __tablename__ = "consignments"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("marketplace_accounts.id"), index=True)
    marketplace: Mapped[Marketplace] = mapped_column(Enum(Marketplace, name="marketplace"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    reference_number: Mapped[str | None] = mapped_column(String(180))
    source_file_name: Mapped[str | None] = mapped_column(String(255))
    source_file_sha256: Mapped[str | None] = mapped_column(String(64))
    source_type: Mapped[str] = mapped_column(String(80), default="manual")
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    account: Mapped[MarketplaceAccount] = relationship()
    lines: Mapped[list["ConsignmentLine"]] = relationship(back_populates="consignment", cascade="all, delete-orphan")
    __table_args__ = (Index("ix_consignments_scope", "account_id", "marketplace", "status", "created_at"),)


class ConsignmentLine(TimestampMixin, Base):
    __tablename__ = "consignment_lines"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    consignment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consignments.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("catalog_products.id"))
    source_row: Mapped[int | None] = mapped_column(Integer)
    source_line_key: Mapped[str | None] = mapped_column(String(64))
    merchant_sku: Mapped[str | None] = mapped_column(String(180), index=True)
    asin: Mapped[str | None] = mapped_column(String(40), index=True)
    fnsku: Mapped[str | None] = mapped_column(String(80), index=True)
    fsn: Mapped[str | None] = mapped_column(String(80), index=True)
    listing_id: Mapped[str | None] = mapped_column(String(180), index=True)
    title_snapshot: Mapped[str | None] = mapped_column(Text)
    brand_snapshot: Mapped[str | None] = mapped_column(String(180))
    category_snapshot: Mapped[str | None] = mapped_column(String(180))
    format_key: Mapped[str | None] = mapped_column(String(100), index=True)
    source_quantity: Mapped[int | None] = mapped_column(Integer)
    print_quantity: Mapped[int] = mapped_column(Integer, default=1)
    net_quantity_value: Mapped[int] = mapped_column(Integer, default=1)
    net_quantity_unit: Mapped[str] = mapped_column(String(20), default="N")
    mrp_catalog: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    mrp_override: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    mrp_source: Mapped[str] = mapped_column(String(30), default="missing")
    selected_for_print: Mapped[bool] = mapped_column(Boolean, default=False)
    workflow_state: Mapped[str] = mapped_column(String(30), default="to_print", index=True)
    match_status: Mapped[str] = mapped_column(String(30), default="unmatched")
    match_method: Mapped[str | None] = mapped_column(String(40))
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    label_overrides: Mapped[dict] = mapped_column(JSON, default=dict)
    address_profile_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("address_profiles.id"))
    last_printed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    successful_print_count: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    raw_row: Mapped[dict] = mapped_column(JSON, default=dict)
    consignment: Mapped[Consignment] = relationship(back_populates="lines")
    product: Mapped[CatalogProduct | None] = relationship()


class ConsignmentIssue(Base):
    __tablename__ = "consignment_issues"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    consignment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consignments.id", ondelete="CASCADE"), index=True)
    consignment_line_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("consignment_lines.id", ondelete="CASCADE"), index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    code: Mapped[str] = mapped_column(String(80), index=True)
    field: Mapped[str | None] = mapped_column(String(80))
    message: Mapped[str] = mapped_column(Text)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PrintJob(TimestampMixin, Base):
    __tablename__ = "print_jobs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    consignment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("consignments.id"))
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("marketplace_accounts.id"), index=True)
    marketplace: Mapped[Marketplace] = mapped_column(Enum(Marketplace, name="marketplace"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="ready")
    printer_name: Mapped[str | None] = mapped_column(String(180))
    printer_profile_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("printer_profiles.id"))
    renderer_version: Mapped[str | None] = mapped_column(String(80))
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_simulation: Mapped[bool] = mapped_column(Boolean, default=False)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False)
    renderer_key: Mapped[str | None] = mapped_column(String(100))
    layout_version: Mapped[int | None] = mapped_column(Integer)
    claimed_by_agent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("print_agents.id"))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    claim_token_hash: Mapped[str | None] = mapped_column(String(64))
    idempotency_key: Mapped[str | None] = mapped_column(String(80), unique=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    spool_job_id: Mapped[str | None] = mapped_column(String(120))
    transport_status: Mapped[str | None] = mapped_column(String(40), index=True)
    transport_error_code: Mapped[str | None] = mapped_column(String(80))
    transport_error_message: Mapped[str | None] = mapped_column(Text)
    lines: Mapped[list["PrintJobLine"]] = relationship(cascade="all, delete-orphan")


class PrintJobLine(Base):
    __tablename__ = "print_job_lines"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    print_job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("print_jobs.id", ondelete="CASCADE"))
    consignment_line_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("consignment_lines.id"))
    label_count: Mapped[int] = mapped_column(Integer)
    data_snapshot: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="ready")
    result: Mapped[str | None] = mapped_column(String(30))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_print_job_line_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("print_job_lines.id"))


class PrintJobEvent(Base):
    __tablename__ = "print_job_events"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    print_job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("print_jobs.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PrintArtifact(Base):
    __tablename__ = "print_artifacts"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    print_job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("print_jobs.id", ondelete="CASCADE"), index=True)
    artifact_type: Mapped[str] = mapped_column(String(40), index=True)
    renderer_key: Mapped[str] = mapped_column(String(100))
    renderer_version: Mapped[str] = mapped_column(String(40))
    layout_version: Mapped[int] = mapped_column(Integer)
    printer_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("printer_profiles.id"))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    byte_size: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    content_type: Mapped[str] = mapped_column(String(100))
    encoding: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default="ready")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    __table_args__ = (UniqueConstraint("print_job_id", "artifact_type", "renderer_key", "renderer_version", "layout_version", "printer_profile_id", name="uq_print_artifact_compilation"),)


class PrintAgent(TimestampMixin, Base):
    __tablename__ = "print_agents"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    machine_name: Mapped[str] = mapped_column(String(180), unique=True)
    token_hash: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(30), default="offline", index=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[str | None] = mapped_column(String(40))
    token_hint: Mapped[str | None] = mapped_column(String(12))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    windows_version: Mapped[str | None] = mapped_column(String(120))
    uptime_seconds: Mapped[int | None] = mapped_column(Integer)
    current_job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("print_jobs.id"))
    last_successful_job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("print_jobs.id"))
    last_error: Mapped[str | None] = mapped_column(Text)


class AgentPairingCode(Base):
    __tablename__ = "agent_pairing_codes"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Printer(TimestampMixin, Base):
    __tablename__ = "printers"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("print_agents.id"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    driver_name: Mapped[str] = mapped_column(String(180))
    dpi: Mapped[int] = mapped_column(Integer, default=203)
    status: Mapped[str] = mapped_column(String(30), default="offline", index=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    port_name: Mapped[str | None] = mapped_column(String(180))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_network: Mapped[bool] = mapped_column(Boolean, default=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (UniqueConstraint("agent_id", "name"),)


class PrinterProfile(TimestampMixin, Base):
    __tablename__ = "printer_profiles"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    printer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("printers.id"), index=True)
    marketplace: Mapped[Marketplace] = mapped_column(Enum(Marketplace, name="marketplace"))
    account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("marketplace_accounts.id"))
    media_width_mm: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    media_height_mm: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    gap_mm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    speed: Mapped[int | None] = mapped_column(Integer)
    darkness: Mapped[int | None] = mapped_column(Integer)
    renderer: Mapped[str] = mapped_column(String(80))
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    layout_version: Mapped[int] = mapped_column(Integer, default=1)


class RendererProfileApproval(Base):
    __tablename__ = "renderer_profile_approvals"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    printer_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("printer_profiles.id", ondelete="CASCADE"), index=True)
    renderer_key: Mapped[str] = mapped_column(String(100))
    renderer_version: Mapped[str] = mapped_column(String(40))
    layout_version: Mapped[int] = mapped_column(Integer)
    format_key: Mapped[str | None] = mapped_column(String(100))
    marketplace: Mapped[Marketplace] = mapped_column(Enum(Marketplace, name="marketplace"))
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    test_print_job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("print_jobs.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (Index("ix_renderer_approval_lookup", "printer_profile_id", "renderer_key", "renderer_version", "layout_version", "format_key", "revoked_at"),)


class BarcodeVerification(Base):
    __tablename__ = "barcode_verifications"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    print_job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("print_jobs.id", ondelete="CASCADE"), index=True)
    print_job_line_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("print_job_lines.id"))
    expected_value: Mapped[str] = mapped_column(String(180))
    scanned_value: Mapped[str] = mapped_column(String(180))
    passed: Mapped[bool] = mapped_column(Boolean)
    verified_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProfileBase(TimestampMixin):
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("marketplace_accounts.id"))
    config: Mapped[dict] = mapped_column(JSON, default=dict)


class AddressProfile(ProfileBase, Base):
    __tablename__ = "address_profiles"
    marketed_by: Mapped[str] = mapped_column(Text)
    address_line_1: Mapped[str] = mapped_column(Text)
    address_line_2: Mapped[str | None] = mapped_column(Text)
    city_state: Mapped[str] = mapped_column(String(180))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(40))
    origin: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

class MappingProfile(ProfileBase, Base): __tablename__ = "mapping_profiles"
class LabelFormatProfile(ProfileBase, Base):
    __tablename__ = "label_format_profiles"
    key: Mapped[str] = mapped_column(String(100), index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    marketplace: Mapped[Marketplace | None] = mapped_column(Enum(Marketplace, name="marketplace"))
    generic_name: Mapped[str | None] = mapped_column(String(180))
    required_fields: Mapped[list] = mapped_column(JSON, default=list)
    field_order: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    entity_type: Mapped[str] = mapped_column(String(60), index=True)
    entity_id: Mapped[str] = mapped_column(String(80), index=True)
    action: Mapped[str] = mapped_column(String(60))
    changes: Mapped[dict] = mapped_column(JSON, default=dict)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
