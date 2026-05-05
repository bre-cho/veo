"""add ownership and billing usage

Revision ID: 20260505_0002
Revises: 20260505_0001
Create Date: 2026-05-05 00:10:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260505_0002"
down_revision = "20260505_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("brands", sa.Column("owner_user_id", sa.String(), nullable=False, server_default="system"))
    op.add_column("projects", sa.Column("owner_user_id", sa.String(), nullable=False, server_default="system"))

    op.create_table(
        "billing_usage",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("owner_user_id", sa.String(), nullable=False),
        sa.Column("brand_id", sa.String(), nullable=True),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("units", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_brands_owner_user_id", "brands", ["owner_user_id"])
    op.create_index("ix_projects_owner_user_id", "projects", ["owner_user_id"])
    op.create_index("ix_billing_usage_owner_user_id", "billing_usage", ["owner_user_id"])
    op.create_index("ix_billing_usage_created_at", "billing_usage", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_billing_usage_created_at", table_name="billing_usage")
    op.drop_index("ix_billing_usage_owner_user_id", table_name="billing_usage")
    op.drop_index("ix_projects_owner_user_id", table_name="projects")
    op.drop_index("ix_brands_owner_user_id", table_name="brands")

    op.drop_table("billing_usage")
    op.drop_column("projects", "owner_user_id")
    op.drop_column("brands", "owner_user_id")