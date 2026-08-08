# pyright: reportAttributeAccessIssue=false
"""Phase 2 consignment operations and immutable print preparation.

Revision ID: 20260809_0002
Revises: 20260808_0001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260809_0002"
down_revision = "20260808_0001"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSON = postgresql.JSONB(astext_type=sa.Text())
marketplace = postgresql.ENUM("AMAZON", "FLIPKART", name="marketplace", create_type=False)


def upgrade() -> None:
    for column in (
        sa.Column("marketplace", marketplace), sa.Column("reference_number", sa.String(180)),
        sa.Column("source_file_name", sa.String(255)), sa.Column("source_file_sha256", sa.String(64)),
        sa.Column("source_type", sa.String(80), server_default="manual", nullable=False),
        sa.Column("created_by_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("metadata", JSON, server_default=sa.text("'{}'::jsonb"), nullable=False),
    ): op.add_column("consignments", column)
    op.execute("UPDATE consignments c SET marketplace=a.marketplace FROM marketplace_accounts a WHERE c.account_id=a.id")
    op.alter_column("consignments", "marketplace", nullable=False)
    op.create_index("ix_consignments_account_id", "consignments", ["account_id"])
    op.create_index("ix_consignments_marketplace", "consignments", ["marketplace"])
    op.create_index("ix_consignments_status", "consignments", ["status"])
    op.create_index("ix_consignments_scope", "consignments", ["account_id", "marketplace", "status", "created_at"])

    op.alter_column("consignment_lines", "quantity", new_column_name="source_quantity")
    op.alter_column("consignment_lines", "net_quantity", new_column_name="net_quantity_value")
    for column in (
        sa.Column("source_row", sa.Integer()), sa.Column("source_line_key", sa.String(64)),
        sa.Column("merchant_sku", sa.String(180)), sa.Column("asin", sa.String(40)),
        sa.Column("fnsku", sa.String(80)), sa.Column("fsn", sa.String(80)),
        sa.Column("listing_id", sa.String(180)), sa.Column("title_snapshot", sa.Text()),
        sa.Column("brand_snapshot", sa.String(180)), sa.Column("category_snapshot", sa.String(180)),
        sa.Column("format_key", sa.String(100)), sa.Column("print_quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("net_quantity_unit", sa.String(20), server_default="N", nullable=False),
        sa.Column("mrp_catalog", sa.Numeric(12, 2)), sa.Column("mrp_override", sa.Numeric(12, 2)),
        sa.Column("mrp_source", sa.String(30), server_default="missing", nullable=False),
        sa.Column("selected_for_print", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("workflow_state", sa.String(30), server_default="to_print", nullable=False),
        sa.Column("match_status", sa.String(30), server_default="unmatched", nullable=False),
        sa.Column("match_method", sa.String(40)), sa.Column("error_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("label_overrides", JSON, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("address_profile_id", UUID, sa.ForeignKey("address_profiles.id")),
        sa.Column("last_printed_at", sa.DateTime(timezone=True)),
        sa.Column("successful_print_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ): op.add_column("consignment_lines", column)
    op.execute("UPDATE consignment_lines SET net_quantity_value=1 WHERE net_quantity_value IS NULL")
    op.alter_column("consignment_lines", "net_quantity_value", nullable=False, server_default="1")
    for name in ("merchant_sku", "asin", "fnsku", "fsn", "listing_id", "format_key", "workflow_state"):
        op.create_index(f"ix_consignment_lines_{name}", "consignment_lines", [name])

    op.create_table("consignment_issues",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("consignment_id", UUID, sa.ForeignKey("consignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consignment_line_id", UUID, sa.ForeignKey("consignment_lines.id", ondelete="CASCADE")),
        sa.Column("severity", sa.String(20), nullable=False), sa.Column("code", sa.String(80), nullable=False),
        sa.Column("field", sa.String(80)), sa.Column("message", sa.Text(), nullable=False),
        sa.Column("resolved", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("resolved_by_id", UUID, sa.ForeignKey("users.id")), sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    for name in ("consignment_id", "consignment_line_id", "severity", "code", "resolved"):
        op.create_index(f"ix_consignment_issues_{name}", "consignment_issues", [name])

    for column in (
        sa.Column("account_id", UUID, sa.ForeignKey("marketplace_accounts.id")),
        sa.Column("marketplace", marketplace), sa.Column("printer_profile_id", UUID, sa.ForeignKey("printer_profiles.id")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("is_simulation", sa.Boolean(), server_default=sa.false(), nullable=False),
    ): op.add_column("print_jobs", column)
    op.execute("UPDATE print_jobs j SET account_id=c.account_id, marketplace=c.marketplace FROM consignments c WHERE j.consignment_id=c.id")
    op.alter_column("print_jobs", "account_id", nullable=False)
    op.alter_column("print_jobs", "marketplace", nullable=False)
    op.create_index("ix_print_jobs_account_id", "print_jobs", ["account_id"])
    op.create_index("ix_print_jobs_marketplace", "print_jobs", ["marketplace"])
    for column in (
        sa.Column("status", sa.String(30), server_default="ready", nullable=False),
        sa.Column("result", sa.String(30)), sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("source_print_job_line_id", UUID, sa.ForeignKey("print_job_lines.id")),
    ): op.add_column("print_job_lines", column)
    op.create_table("print_job_events", sa.Column("id", UUID, primary_key=True),
        sa.Column("print_job_id", UUID, sa.ForeignKey("print_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False), sa.Column("actor_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("payload", JSON, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_print_job_events_print_job_id", "print_job_events", ["print_job_id"])
    op.create_index("ix_print_job_events_event_type", "print_job_events", ["event_type"])

    for column in (
        sa.Column("marketed_by", sa.Text(), server_default="", nullable=False),
        sa.Column("address_line_1", sa.Text(), server_default="", nullable=False),
        sa.Column("address_line_2", sa.Text()), sa.Column("city_state", sa.String(180), server_default="", nullable=False),
        sa.Column("email", sa.String(255)), sa.Column("phone", sa.String(40)), sa.Column("origin", sa.String(120)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.false(), nullable=False),
    ): op.add_column("address_profiles", column)
    for column in (
        sa.Column("key", sa.String(100)), sa.Column("display_name", sa.String(120)),
        sa.Column("marketplace", marketplace), sa.Column("generic_name", sa.String(180)),
        sa.Column("required_fields", JSON, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("field_order", JSON, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
    ): op.add_column("label_format_profiles", column)
    op.execute("UPDATE label_format_profiles SET key=lower(regexp_replace(name, '[^a-zA-Z0-9]+', '_', 'g')), display_name=name")
    op.alter_column("label_format_profiles", "key", nullable=False)
    op.alter_column("label_format_profiles", "display_name", nullable=False)
    op.create_index("ix_label_format_profiles_key", "label_format_profiles", ["key"])


def downgrade() -> None:
    op.drop_index("ix_label_format_profiles_key", table_name="label_format_profiles")
    for name in ("is_active", "field_order", "required_fields", "generic_name", "marketplace", "display_name", "key"):
        op.drop_column("label_format_profiles", name)
    for name in ("is_default", "is_active", "origin", "phone", "email", "city_state", "address_line_2", "address_line_1", "marketed_by"):
        op.drop_column("address_profiles", name)
    op.drop_table("print_job_events")
    for name in ("source_print_job_line_id", "completed_at", "result", "status"): op.drop_column("print_job_lines", name)
    for name in ("is_simulation", "completed_at", "printer_profile_id", "marketplace", "account_id"): op.drop_column("print_jobs", name)
    op.drop_table("consignment_issues")
    for name in ("updated_at", "created_at", "version", "successful_print_count", "last_printed_at", "address_profile_id", "label_overrides", "error_count", "match_method", "match_status", "workflow_state", "selected_for_print", "mrp_source", "mrp_override", "mrp_catalog", "net_quantity_unit", "print_quantity", "format_key", "category_snapshot", "brand_snapshot", "title_snapshot", "listing_id", "fsn", "fnsku", "asin", "merchant_sku", "source_line_key", "source_row"):
        op.drop_column("consignment_lines", name)
    op.alter_column("consignment_lines", "net_quantity_value", new_column_name="net_quantity")
    op.alter_column("consignment_lines", "source_quantity", new_column_name="quantity")
    for name in ("metadata", "completed_at", "created_by_id", "source_type", "source_file_sha256", "source_file_name", "reference_number", "marketplace"):
        op.drop_column("consignments", name)
