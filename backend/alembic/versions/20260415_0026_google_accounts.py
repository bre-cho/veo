"""add google_accounts table for multi-account rotation

Revision ID: 20260415_0026
Revises: 20260412_9999
Create Date: 2026-04-15 03:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260415_0026"
down_revision = "20260412_9999"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "google_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("gemini_api_key", sa.Text(), nullable=True),
        sa.Column("google_cloud_project", sa.Text(), nullable=True),
        sa.Column("google_cloud_location", sa.Text(), nullable=False),
        sa.Column("gcs_output_uri", sa.Text(), nullable=True),
        sa.Column("use_vertex", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("rotation_enabled", sa.Boolean(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("google_accounts")
