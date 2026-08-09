"""Phase 3.1 production gate hardening.

Revision ID: 20260811_0004
Revises: 20260810_0003
"""
from alembic import op
import sqlalchemy as sa

revision="20260811_0004"
down_revision="20260810_0003"
branch_labels=None
depends_on=None


def upgrade()->None:
    op.add_column("renderer_profile_approvals",sa.Column("font_fingerprint",sa.String(64)))
    op.add_column("printers",sa.Column("last_error",sa.Text()))
    op.execute("INSERT INTO roles (name) VALUES ('Admin'),('QC'),('Packing'),('Print Operator') ON CONFLICT (name) DO NOTHING")


def downgrade()->None:
    op.drop_column("printers","last_error")
    op.drop_column("renderer_profile_approvals","font_fingerprint")
