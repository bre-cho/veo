"""Add phase8 storyboard optimization memory tables

Revision ID: 20260420_0032
Revises: 20260420_0031
Create Date: 2026-04-20 05:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260420_0032"
down_revision = "20260420_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pattern_memories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("pattern_type", sa.String(length=64), nullable=False),
        sa.Column("market_code", sa.String(length=32), nullable=True),
        sa.Column("content_goal", sa.String(length=64), nullable=True),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column("score", sa.Numeric(8, 4), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pattern_memories_pattern_type", "pattern_memories", ["pattern_type"])
    op.create_index("ix_pattern_memories_market_code", "pattern_memories", ["market_code"])
    op.create_index("ix_pattern_memories_content_goal", "pattern_memories", ["content_goal"])
    op.create_index("ix_pattern_memories_source_id", "pattern_memories", ["source_id"])
    op.create_index("ix_pattern_memories_created_at", "pattern_memories", ["created_at"])

    op.create_table(
        "optimization_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("render_job_id", sa.String(length=36), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("output", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_optimization_runs_project_id", "optimization_runs", ["project_id"])
    op.create_index("ix_optimization_runs_render_job_id", "optimization_runs", ["render_job_id"])
    op.create_index("ix_optimization_runs_created_at", "optimization_runs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_optimization_runs_created_at", table_name="optimization_runs")
    op.drop_index("ix_optimization_runs_render_job_id", table_name="optimization_runs")
    op.drop_index("ix_optimization_runs_project_id", table_name="optimization_runs")
    op.drop_table("optimization_runs")

    op.drop_index("ix_pattern_memories_created_at", table_name="pattern_memories")
    op.drop_index("ix_pattern_memories_source_id", table_name="pattern_memories")
    op.drop_index("ix_pattern_memories_content_goal", table_name="pattern_memories")
    op.drop_index("ix_pattern_memories_market_code", table_name="pattern_memories")
    op.drop_index("ix_pattern_memories_pattern_type", table_name="pattern_memories")
    op.drop_table("pattern_memories")
