# pyright: reportAttributeAccessIssue=false
"""Phase 3 print agent, renderer approvals, and immutable artifacts.

Revision ID: 20260810_0003
Revises: 20260809_0002
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260810_0003"
down_revision = "20260809_0002"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSON = postgresql.JSONB(astext_type=sa.Text())
marketplace = postgresql.ENUM("AMAZON", "FLIPKART", name="marketplace", create_type=False)


def upgrade() -> None:
    op.execute("CREATE INDEX ix_catalog_products_account_sku_normalized ON catalog_products (account_id, lower(btrim(sku)))")
    op.execute("CREATE INDEX ix_catalog_identifiers_kind_value_normalized ON catalog_identifiers (lower(kind), lower(btrim(value)), product_id)")

    for column in (
        sa.Column("is_test", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("renderer_key", sa.String(100)), sa.Column("layout_version", sa.Integer()),
        sa.Column("claimed_by_agent_id", UUID), sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)), sa.Column("claim_token_hash", sa.String(64)),
        sa.Column("idempotency_key", sa.String(80)), sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)), sa.Column("spool_job_id", sa.String(120)),
        sa.Column("transport_status", sa.String(40)), sa.Column("transport_error_code", sa.String(80)),
        sa.Column("transport_error_message", sa.Text()),
    ): op.add_column("print_jobs", column)
    op.create_foreign_key("fk_print_jobs_claimed_agent", "print_jobs", "print_agents", ["claimed_by_agent_id"], ["id"])
    op.create_unique_constraint("uq_print_jobs_idempotency_key", "print_jobs", ["idempotency_key"])
    op.create_index("ix_print_jobs_lease_expires_at", "print_jobs", ["lease_expires_at"])
    op.create_index("ix_print_jobs_transport_status", "print_jobs", ["transport_status"])

    for column in (
        sa.Column("token_hint", sa.String(12)), sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("windows_version", sa.String(120)), sa.Column("uptime_seconds", sa.Integer()),
        sa.Column("current_job_id", UUID), sa.Column("last_successful_job_id", UUID), sa.Column("last_error", sa.Text()),
    ): op.add_column("print_agents", column)
    op.create_index("ix_print_agents_token_hash", "print_agents", ["token_hash"])
    op.create_foreign_key("fk_print_agents_current_job", "print_agents", "print_jobs", ["current_job_id"], ["id"])
    op.create_foreign_key("fk_print_agents_last_successful_job", "print_agents", "print_jobs", ["last_successful_job_id"], ["id"])

    for column in (
        sa.Column("port_name", sa.String(180)), sa.Column("is_default", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_network", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
    ): op.add_column("printers", column)
    op.add_column("printer_profiles", sa.Column("layout_version", sa.Integer(), server_default="1", nullable=False))

    op.create_table("agent_pairing_codes",
        sa.Column("id", UUID, primary_key=True), sa.Column("code_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("created_by_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_agent_pairing_codes_code_hash", "agent_pairing_codes", ["code_hash"], unique=True)
    op.create_index("ix_agent_pairing_codes_expires_at", "agent_pairing_codes", ["expires_at"])

    op.create_table("print_artifacts",
        sa.Column("id", UUID, primary_key=True), sa.Column("print_job_id", UUID, sa.ForeignKey("print_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_type", sa.String(40), nullable=False), sa.Column("renderer_key", sa.String(100), nullable=False),
        sa.Column("renderer_version", sa.String(40), nullable=False), sa.Column("layout_version", sa.Integer(), nullable=False),
        sa.Column("printer_profile_id", UUID, sa.ForeignKey("printer_profiles.id"), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False), sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False, unique=True), sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("encoding", sa.String(40)), sa.Column("status", sa.String(30), server_default="ready", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("metadata", JSON, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.UniqueConstraint("print_job_id", "artifact_type", "renderer_key", "renderer_version", "layout_version", "printer_profile_id", name="uq_print_artifact_compilation"))
    op.create_index("ix_print_artifacts_print_job_id", "print_artifacts", ["print_job_id"])
    op.create_index("ix_print_artifacts_artifact_type", "print_artifacts", ["artifact_type"])
    op.create_index("ix_print_artifacts_sha256", "print_artifacts", ["sha256"])

    op.create_table("renderer_profile_approvals",
        sa.Column("id", UUID, primary_key=True), sa.Column("printer_profile_id", UUID, sa.ForeignKey("printer_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("renderer_key", sa.String(100), nullable=False), sa.Column("renderer_version", sa.String(40), nullable=False),
        sa.Column("layout_version", sa.Integer(), nullable=False), sa.Column("format_key", sa.String(100)),
        sa.Column("marketplace", marketplace, nullable=False), sa.Column("approved_by_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("approved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("test_print_job_id", UUID, sa.ForeignKey("print_jobs.id"), nullable=False), sa.Column("notes", sa.Text()),
        sa.Column("revoked_at", sa.DateTime(timezone=True)))
    op.create_index("ix_renderer_profile_approvals_printer_profile_id", "renderer_profile_approvals", ["printer_profile_id"])
    op.create_index("ix_renderer_approval_lookup", "renderer_profile_approvals", ["printer_profile_id", "renderer_key", "renderer_version", "layout_version", "format_key", "revoked_at"])

    op.create_table("barcode_verifications",
        sa.Column("id", UUID, primary_key=True), sa.Column("print_job_id", UUID, sa.ForeignKey("print_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("print_job_line_id", UUID, sa.ForeignKey("print_job_lines.id")), sa.Column("expected_value", sa.String(180), nullable=False),
        sa.Column("scanned_value", sa.String(180), nullable=False), sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("verified_by_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("verified_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_barcode_verifications_print_job_id", "barcode_verifications", ["print_job_id"])


def downgrade() -> None:
    op.drop_table("barcode_verifications")
    op.drop_table("renderer_profile_approvals")
    op.drop_table("print_artifacts")
    op.drop_table("agent_pairing_codes")
    op.drop_column("printer_profiles", "layout_version")
    for name in ("is_enabled", "is_network", "is_default", "port_name"): op.drop_column("printers", name)
    op.drop_constraint("fk_print_agents_last_successful_job", "print_agents", type_="foreignkey")
    op.drop_constraint("fk_print_agents_current_job", "print_agents", type_="foreignkey")
    op.drop_index("ix_print_agents_token_hash", table_name="print_agents")
    for name in ("last_error", "last_successful_job_id", "current_job_id", "uptime_seconds", "windows_version", "revoked_at", "token_hint"): op.drop_column("print_agents", name)
    op.drop_constraint("fk_print_jobs_claimed_agent", "print_jobs", type_="foreignkey")
    op.drop_constraint("uq_print_jobs_idempotency_key", "print_jobs", type_="unique")
    for name in ("transport_error_message", "transport_error_code", "transport_status", "spool_job_id", "last_attempt_at", "attempt_count", "idempotency_key", "claim_token_hash", "lease_expires_at", "claimed_at", "claimed_by_agent_id", "layout_version", "renderer_key", "is_test"): op.drop_column("print_jobs", name)
    op.execute("DROP INDEX IF EXISTS ix_catalog_identifiers_kind_value_normalized")
    op.execute("DROP INDEX IF EXISTS ix_catalog_products_account_sku_normalized")
