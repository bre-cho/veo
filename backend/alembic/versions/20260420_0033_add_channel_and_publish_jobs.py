"""Add channel plan and publish jobs tables

Revision ID: 20260420_0033
Revises: 20260420_0032
Create Date: 2026-04-20 05:05:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260420_0033"
down_revision = "20260420_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "channel_plans",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("channel_name", sa.String(length=128), nullable=True),
        sa.Column("niche", sa.String(length=128), nullable=False),
        sa.Column("market_code", sa.String(length=32), nullable=True),
        sa.Column("goal", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_channel_plans_channel_name", "channel_plans", ["channel_name"])
    op.create_index("ix_channel_plans_niche", "channel_plans", ["niche"])
    op.create_index("ix_channel_plans_market_code", "channel_plans", ["market_code"])

    op.create_table(
        "publish_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("channel_plan_id", sa.String(length=36), nullable=True),
        sa.Column("platform", sa.String(length=64), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="scheduled"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_publish_jobs_channel_plan_id", "publish_jobs", ["channel_plan_id"])
    op.create_index("ix_publish_jobs_platform", "publish_jobs", ["platform"])
    op.create_index("ix_publish_jobs_scheduled_for", "publish_jobs", ["scheduled_for"])
    op.create_index("ix_publish_jobs_status", "publish_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_publish_jobs_status", table_name="publish_jobs")
    op.drop_index("ix_publish_jobs_scheduled_for", table_name="publish_jobs")
    op.drop_index("ix_publish_jobs_platform", table_name="publish_jobs")
    op.drop_index("ix_publish_jobs_channel_plan_id", table_name="publish_jobs")
    op.drop_table("publish_jobs")

    op.drop_index("ix_channel_plans_market_code", table_name="channel_plans")
    op.drop_index("ix_channel_plans_niche", table_name="channel_plans")
    op.drop_index("ix_channel_plans_channel_name", table_name="channel_plans")
    op.drop_table("channel_plans")
