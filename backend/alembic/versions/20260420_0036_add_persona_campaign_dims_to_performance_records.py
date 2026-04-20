"""Add persona_id, product_category, funnel_stage, campaign_id to performance_records

Revision ID: 20260420_0036
Revises: 20260420_0035
Create Date: 2026-04-20 10:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260420_0036"
down_revision = "20260420_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Phase 1.1: persona / product-category / funnel dimensions
    op.add_column(
        "performance_records",
        sa.Column("persona_id", sa.String(length=128), nullable=True),
    )
    op.create_index("ix_performance_records_persona_id", "performance_records", ["persona_id"])
    op.add_column(
        "performance_records",
        sa.Column("product_category", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_performance_records_product_category", "performance_records", ["product_category"]
    )
    op.add_column(
        "performance_records",
        sa.Column("funnel_stage", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_performance_records_funnel_stage", "performance_records", ["funnel_stage"])

    # Phase 1.2: campaign attribution
    op.add_column(
        "performance_records",
        sa.Column("campaign_id", sa.String(length=128), nullable=True),
    )
    op.create_index("ix_performance_records_campaign_id", "performance_records", ["campaign_id"])

    # Phase 3.1: provider_metadata on publish_jobs
    op.add_column(
        "publish_jobs",
        sa.Column("provider_metadata", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("publish_jobs", "provider_metadata")

    op.drop_index("ix_performance_records_campaign_id", table_name="performance_records")
    op.drop_column("performance_records", "campaign_id")
    op.drop_index("ix_performance_records_funnel_stage", table_name="performance_records")
    op.drop_column("performance_records", "funnel_stage")
    op.drop_index("ix_performance_records_product_category", table_name="performance_records")
    op.drop_column("performance_records", "product_category")
    op.drop_index("ix_performance_records_persona_id", table_name="performance_records")
    op.drop_column("performance_records", "persona_id")
