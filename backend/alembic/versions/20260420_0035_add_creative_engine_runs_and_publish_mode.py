"""Add publish_mode to publish_jobs and create creative_engine_runs table

Revision ID: 20260420_0035
Revises: 20260420_0034
Create Date: 2026-04-20 07:30:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260420_0035"
down_revision = "20260420_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add publish_mode column to publish_jobs so QA can see SIMULATED vs REAL
    op.add_column(
        "publish_jobs",
        sa.Column("publish_mode", sa.String(length=16), nullable=False, server_default="SIMULATED"),
    )
    op.create_index("ix_publish_jobs_publish_mode", "publish_jobs", ["publish_mode"])

    # Create creative_engine_runs table for shared run history
    op.create_table(
        "creative_engine_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("engine_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("input_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("candidates", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("winner_candidate_id", sa.String(length=128), nullable=True),
        sa.Column("output_payload", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.String(length=2048), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parent_run_id", sa.String(length=36), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_creative_engine_runs_engine_type", "creative_engine_runs", ["engine_type"])
    op.create_index("ix_creative_engine_runs_status", "creative_engine_runs", ["status"])
    op.create_index("ix_creative_engine_runs_parent_run_id", "creative_engine_runs", ["parent_run_id"])
    op.create_index("ix_creative_engine_runs_created_at", "creative_engine_runs", ["created_at"])
    op.create_index("ix_creative_engine_runs_updated_at", "creative_engine_runs", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_creative_engine_runs_updated_at", table_name="creative_engine_runs")
    op.drop_index("ix_creative_engine_runs_created_at", table_name="creative_engine_runs")
    op.drop_index("ix_creative_engine_runs_parent_run_id", table_name="creative_engine_runs")
    op.drop_index("ix_creative_engine_runs_status", table_name="creative_engine_runs")
    op.drop_index("ix_creative_engine_runs_engine_type", table_name="creative_engine_runs")
    op.drop_table("creative_engine_runs")

    op.drop_index("ix_publish_jobs_publish_mode", table_name="publish_jobs")
    op.drop_column("publish_jobs", "publish_mode")
