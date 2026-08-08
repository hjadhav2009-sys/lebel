# pyright: reportAttributeAccessIssue=false
"""Explicit initial MMS web schema.

Revision ID: 20260808_0001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260808_0001"
down_revision = None
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSON = postgresql.JSONB(astext_type=sa.Text())
marketplace = sa.Enum("AMAZON", "FLIPKART", name="marketplace")
import_status = sa.Enum("PENDING", "PROCESSING", "COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED", name="import_status")
row_action = sa.Enum("NEW", "UPDATED", "UNCHANGED", "ERROR", name="row_action")


def timestamps():
    return [sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)]


def upgrade() -> None:
    bind = op.get_bind()
    marketplace.create(bind, checkfirst=True); import_status.create(bind, checkfirst=True); row_action.create(bind, checkfirst=True)
    op.create_table("roles", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(40), nullable=False, unique=True))
    op.create_table("users", sa.Column("id", UUID, primary_key=True), sa.Column("email", sa.String(255), nullable=False, unique=True), sa.Column("display_name", sa.String(120), nullable=False), sa.Column("password_hash", sa.String(255)), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), *timestamps())
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("user_roles", sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True), sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True))
    op.create_table("marketplace_accounts", sa.Column("id", UUID, primary_key=True), sa.Column("marketplace", marketplace, nullable=False), sa.Column("name", sa.String(120), nullable=False), sa.Column("external_id", sa.String(120)), sa.Column("default_address_profile_id", UUID), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), *timestamps(), sa.UniqueConstraint("marketplace", "name"))
    op.create_index("ix_marketplace_accounts_marketplace", "marketplace_accounts", ["marketplace"])
    op.create_table("catalog_batches", sa.Column("id", UUID, primary_key=True), sa.Column("account_id", UUID, sa.ForeignKey("marketplace_accounts.id"), nullable=False), sa.Column("marketplace", marketplace, nullable=False), sa.Column("name", sa.String(180), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("created_by_id", UUID, sa.ForeignKey("users.id")), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_catalog_batches_account_id", "catalog_batches", ["account_id"])
    op.create_table("catalog_imports", sa.Column("id", UUID, primary_key=True), sa.Column("batch_id", UUID, sa.ForeignKey("catalog_batches.id")), sa.Column("account_id", UUID, sa.ForeignKey("marketplace_accounts.id"), nullable=False), sa.Column("source_file", sa.String(255), nullable=False), sa.Column("original_filename", sa.String(255), nullable=False), sa.Column("sheet_name", sa.String(255)), sa.Column("file_sha256", sa.String(64), nullable=False), sa.Column("file_size", sa.Integer(), nullable=False), sa.Column("mapping", JSON, nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("detected_type", sa.String(80)), sa.Column("status", import_status, nullable=False), sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"), sa.Column("new_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("unchanged_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("created_by_id", UUID, sa.ForeignKey("users.id")), *timestamps())
    for name, columns in (("ix_catalog_imports_batch_id", ["batch_id"]), ("ix_catalog_imports_account_id", ["account_id"]), ("ix_catalog_imports_file_sha256", ["file_sha256"])): op.create_index(name, "catalog_imports", columns)
    op.create_table("catalog_products", sa.Column("id", UUID, primary_key=True), sa.Column("account_id", UUID, sa.ForeignKey("marketplace_accounts.id"), nullable=False), sa.Column("business_key", sa.String(320), nullable=False), sa.Column("row_hash", sa.String(64), nullable=False), sa.Column("sku", sa.String(180)), sa.Column("title", sa.Text()), sa.Column("brand", sa.String(180)), sa.Column("mrp", sa.Numeric(12, 2)), sa.Column("category", sa.String(180)), sa.Column("source_file", sa.String(255)), sa.Column("source_template", sa.String(120)), sa.Column("source_category", sa.String(180)), sa.Column("extra_attributes", JSON, nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("last_import_id", UUID, sa.ForeignKey("catalog_imports.id")), *timestamps(), sa.UniqueConstraint("account_id", "business_key"))
    op.create_index("ix_catalog_search", "catalog_products", ["account_id", "sku", "category"]); op.create_index("ix_catalog_products_updated_at", "catalog_products", ["updated_at"])
    op.create_table("catalog_identifiers", sa.Column("id", UUID, primary_key=True), sa.Column("product_id", UUID, sa.ForeignKey("catalog_products.id", ondelete="CASCADE"), nullable=False), sa.Column("kind", sa.String(30), nullable=False), sa.Column("value", sa.String(180), nullable=False), sa.Column("source", sa.String(40), nullable=False), sa.Column("authoritative_source", sa.String(120)), sa.UniqueConstraint("product_id", "kind", "value"))
    op.create_index("ix_catalog_identifiers_kind_value", "catalog_identifiers", ["kind", "value"]); op.create_index("ix_catalog_identifiers_product_id", "catalog_identifiers", ["product_id"])
    op.create_table("product_images", sa.Column("id", UUID, primary_key=True), sa.Column("product_id", UUID, sa.ForeignKey("catalog_products.id", ondelete="CASCADE"), nullable=False), sa.Column("url", sa.Text(), nullable=False), sa.Column("cached_url", sa.Text()), sa.Column("kind", sa.String(30), nullable=False), sa.Column("position", sa.Integer(), nullable=False), sa.Column("source", sa.String(40), nullable=False), sa.Column("source_reference", sa.String(180)), sa.Column("last_checked_at", sa.DateTime(timezone=True)), sa.Column("status", sa.String(30), nullable=False), sa.UniqueConstraint("product_id", "url"))
    op.create_index("ix_product_images_product_id", "product_images", ["product_id"])
    op.create_table("catalog_import_rows", sa.Column("id", UUID, primary_key=True), sa.Column("import_id", UUID, sa.ForeignKey("catalog_imports.id", ondelete="CASCADE"), nullable=False), sa.Column("source_row", sa.Integer(), nullable=False), sa.Column("business_key", sa.String(320)), sa.Column("row_hash", sa.String(64)), sa.Column("action", row_action, nullable=False), sa.Column("raw_row", JSON, nullable=False), sa.Column("normalized_row", JSON), sa.Column("product_id", UUID, sa.ForeignKey("catalog_products.id")), sa.UniqueConstraint("import_id", "source_row"))
    op.create_index("ix_catalog_import_rows_import_id", "catalog_import_rows", ["import_id"])
    op.create_table("import_errors", sa.Column("id", UUID, primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("import_id", UUID, sa.ForeignKey("catalog_imports.id")), sa.Column("import_row_id", UUID, sa.ForeignKey("catalog_import_rows.id")), sa.Column("severity", sa.String(20), nullable=False), sa.Column("marketplace", sa.String(30), nullable=False), sa.Column("account", sa.String(120)), sa.Column("source_file", sa.String(255)), sa.Column("source_row", sa.Integer()), sa.Column("product_identifier", sa.String(180)), sa.Column("field", sa.String(80)), sa.Column("code", sa.String(80), nullable=False), sa.Column("message", sa.Text(), nullable=False), sa.Column("suggested_action", sa.Text()), sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("resolved_by_id", UUID, sa.ForeignKey("users.id")), sa.Column("resolved_at", sa.DateTime(timezone=True)))
    op.create_index("ix_import_errors_code_resolved", "import_errors", ["code", "resolved"]); op.create_index("ix_import_errors_import_id_source_row", "import_errors", ["import_id", "source_row"])
    op.create_table("consignments", sa.Column("id", UUID, primary_key=True), sa.Column("account_id", UUID, sa.ForeignKey("marketplace_accounts.id"), nullable=False), sa.Column("name", sa.String(180), nullable=False), sa.Column("status", sa.String(30), nullable=False), *timestamps())
    op.create_table("consignment_lines", sa.Column("id", UUID, primary_key=True), sa.Column("consignment_id", UUID, sa.ForeignKey("consignments.id", ondelete="CASCADE"), nullable=False), sa.Column("product_id", UUID, sa.ForeignKey("catalog_products.id")), sa.Column("quantity", sa.Integer()), sa.Column("net_quantity", sa.Integer()), sa.Column("raw_row", JSON, nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.create_index("ix_consignment_lines_consignment_id", "consignment_lines", ["consignment_id"])
    op.create_table("print_jobs", sa.Column("id", UUID, primary_key=True), sa.Column("consignment_id", UUID, sa.ForeignKey("consignments.id")), sa.Column("status", sa.String(30), nullable=False), sa.Column("printer_name", sa.String(180)), sa.Column("renderer_version", sa.String(80)), sa.Column("created_by_id", UUID, sa.ForeignKey("users.id")), *timestamps())
    op.create_table("print_job_lines", sa.Column("id", UUID, primary_key=True), sa.Column("print_job_id", UUID, sa.ForeignKey("print_jobs.id", ondelete="CASCADE"), nullable=False), sa.Column("consignment_line_id", UUID, sa.ForeignKey("consignment_lines.id")), sa.Column("label_count", sa.Integer(), nullable=False), sa.Column("data_snapshot", JSON, nullable=False))
    op.create_index("ix_print_job_lines_print_job_id", "print_job_lines", ["print_job_id"])
    for table in ("address_profiles", "mapping_profiles", "label_format_profiles"):
        op.create_table(table, sa.Column("id", UUID, primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("account_id", UUID, sa.ForeignKey("marketplace_accounts.id")), sa.Column("config", JSON, nullable=False, server_default=sa.text("'{}'::jsonb")), *timestamps())
    op.create_foreign_key("fk_account_default_address", "marketplace_accounts", "address_profiles", ["default_address_profile_id"], ["id"])
    op.create_table("audit_events", sa.Column("id", UUID, primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("actor_id", UUID, sa.ForeignKey("users.id")), sa.Column("entity_type", sa.String(60), nullable=False), sa.Column("entity_id", sa.String(80), nullable=False), sa.Column("action", sa.String(60), nullable=False), sa.Column("changes", JSON, nullable=False), sa.Column("context", JSON, nullable=False))
    op.create_index("ix_audit_events_entity", "audit_events", ["entity_type", "entity_id"])
    op.create_table("print_agents", sa.Column("id", UUID, primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("machine_name", sa.String(180), nullable=False, unique=True), sa.Column("token_hash", sa.String(255), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("last_seen_at", sa.DateTime(timezone=True)), sa.Column("version", sa.String(40)), *timestamps())
    op.create_table("printers", sa.Column("id", UUID, primary_key=True), sa.Column("agent_id", UUID, sa.ForeignKey("print_agents.id"), nullable=False), sa.Column("name", sa.String(180), nullable=False), sa.Column("driver_name", sa.String(180), nullable=False), sa.Column("dpi", sa.Integer(), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("last_seen_at", sa.DateTime(timezone=True)), *timestamps(), sa.UniqueConstraint("agent_id", "name"))
    op.create_table("printer_profiles", sa.Column("id", UUID, primary_key=True), sa.Column("printer_id", UUID, sa.ForeignKey("printers.id"), nullable=False), sa.Column("marketplace", marketplace, nullable=False), sa.Column("account_id", UUID, sa.ForeignKey("marketplace_accounts.id")), sa.Column("media_width_mm", sa.Numeric(8, 2), nullable=False), sa.Column("media_height_mm", sa.Numeric(8, 2), nullable=False), sa.Column("gap_mm", sa.Numeric(8, 2)), sa.Column("speed", sa.Integer()), sa.Column("darkness", sa.Integer()), sa.Column("renderer", sa.String(80), nullable=False), sa.Column("config", JSON, nullable=False), *timestamps())


def downgrade() -> None:
    op.drop_constraint("fk_account_default_address", "marketplace_accounts", type_="foreignkey")
    for table in ("printer_profiles", "printers", "print_agents", "audit_events", "label_format_profiles", "mapping_profiles", "address_profiles", "print_job_lines", "print_jobs", "consignment_lines", "consignments", "import_errors", "catalog_import_rows", "product_images", "catalog_identifiers", "catalog_products", "catalog_imports", "catalog_batches", "user_roles", "marketplace_accounts", "users", "roles"):
        op.drop_table(table)
    bind = op.get_bind(); row_action.drop(bind, checkfirst=True); import_status.drop(bind, checkfirst=True); marketplace.drop(bind, checkfirst=True)
