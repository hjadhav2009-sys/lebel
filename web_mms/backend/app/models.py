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
    __table_args__ = (UniqueConstraint("account_id", "business_key"), Index("ix_catalog_search", "account_id", "sku", "category"))


class CatalogIdentifier(Base):
    __tablename__ = "catalog_identifiers"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalog_products.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    value: Mapped[str] = mapped_column(String(180), index=True)
    product: Mapped[CatalogProduct] = relationship(back_populates="identifiers")
    __table_args__ = (UniqueConstraint("product_id", "kind"), UniqueConstraint("kind", "value", "product_id"),)


class ProductImage(Base):
    __tablename__ = "product_images"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalog_products.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(30), default="other")
    position: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(40), default="import")
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="available")
    product: Mapped[CatalogProduct] = relationship(back_populates="images")
    __table_args__ = (UniqueConstraint("product_id", "url"),)


class CatalogImport(TimestampMixin, Base):
    __tablename__ = "catalog_imports"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("marketplace_accounts.id"), index=True)
    source_file: Mapped[str] = mapped_column(String(255))
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


class Consignment(TimestampMixin, Base):
    __tablename__ = "consignments"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("marketplace_accounts.id"))
    name: Mapped[str] = mapped_column(String(180))
    status: Mapped[str] = mapped_column(String(30), default="open")


class ConsignmentLine(Base):
    __tablename__ = "consignment_lines"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    consignment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consignments.id", ondelete="CASCADE"))
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("catalog_products.id"))
    quantity: Mapped[int | None] = mapped_column(Integer)
    net_quantity: Mapped[int | None] = mapped_column(Integer)
    raw_row: Mapped[dict] = mapped_column(JSON, default=dict)


class PrintJob(TimestampMixin, Base):
    __tablename__ = "print_jobs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    consignment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("consignments.id"))
    status: Mapped[str] = mapped_column(String(30), default="ready")
    printer_name: Mapped[str | None] = mapped_column(String(180))
    renderer_version: Mapped[str | None] = mapped_column(String(80))
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class PrintJobLine(Base):
    __tablename__ = "print_job_lines"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    print_job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("print_jobs.id", ondelete="CASCADE"))
    consignment_line_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("consignment_lines.id"))
    label_count: Mapped[int] = mapped_column(Integer)
    data_snapshot: Mapped[dict] = mapped_column(JSON)


class ProfileBase(TimestampMixin):
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("marketplace_accounts.id"))
    config: Mapped[dict] = mapped_column(JSON, default=dict)


class AddressProfile(ProfileBase, Base): __tablename__ = "address_profiles"
class MappingProfile(ProfileBase, Base): __tablename__ = "mapping_profiles"
class LabelFormatProfile(ProfileBase, Base): __tablename__ = "label_format_profiles"


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
