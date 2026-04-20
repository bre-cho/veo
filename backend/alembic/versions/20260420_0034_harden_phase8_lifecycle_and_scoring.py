"""Harden phase8 lifecycle, scoring, and trace persistence

Revision ID: 20260420_0034
Revises: 20260420_0033
Create Date: 2026-04-20 06:40:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260420_0034"
down_revision = "20260420_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # optimization_runs
    op.add_column("optimization_runs", sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"))
    op.add_column("optimization_runs", sa.Column("input_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("optimization_runs", sa.Column("output_payload", sa.JSON(), nullable=True))
    op.add_column("optimization_runs", sa.Column("score_summary", sa.JSON(), nullable=True))
    op.add_column("optimization_runs", sa.Column("error_message", sa.String(length=2048), nullable=True))
    op.add_column("optimization_runs", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("optimization_runs", sa.Column("parent_run_id", sa.String(length=36), nullable=True))
    op.add_column("optimization_runs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("optimization_runs", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "optimization_runs",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_optimization_runs_status", "optimization_runs", ["status"])
    op.create_index("ix_optimization_runs_parent_run_id", "optimization_runs", ["parent_run_id"])
    op.create_index("ix_optimization_runs_updated_at", "optimization_runs", ["updated_at"])

    # channel_plans
    op.add_column("channel_plans", sa.Column("project_id", sa.String(length=36), nullable=True))
    op.add_column("channel_plans", sa.Column("avatar_id", sa.String(length=36), nullable=True))
    op.add_column("channel_plans", sa.Column("product_id", sa.String(length=36), nullable=True))
    op.add_column("channel_plans", sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"))
    op.add_column("channel_plans", sa.Column("request_context", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("channel_plans", sa.Column("selected_variants", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("channel_plans", sa.Column("ranking_scores", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("channel_plans", sa.Column("final_plan", sa.JSON(), nullable=True))
    op.add_column("channel_plans", sa.Column("error_message", sa.String(length=2048), nullable=True))
    op.add_column("channel_plans", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("channel_plans", sa.Column("parent_plan_id", sa.String(length=36), nullable=True))
    op.add_column("channel_plans", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("channel_plans", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("channel_plans", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_channel_plans_project_id", "channel_plans", ["project_id"])
    op.create_index("ix_channel_plans_avatar_id", "channel_plans", ["avatar_id"])
    op.create_index("ix_channel_plans_product_id", "channel_plans", ["product_id"])
    op.create_index("ix_channel_plans_status", "channel_plans", ["status"])
    op.create_index("ix_channel_plans_parent_plan_id", "channel_plans", ["parent_plan_id"])
    op.create_index("ix_channel_plans_updated_at", "channel_plans", ["updated_at"])

    # publish_jobs
    op.alter_column("publish_jobs", "status", server_default="queued")
    op.add_column("publish_jobs", sa.Column("request_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("publish_jobs", sa.Column("provider_response", sa.JSON(), nullable=True))
    op.add_column("publish_jobs", sa.Column("external_ids", sa.JSON(), nullable=True))
    op.add_column("publish_jobs", sa.Column("error_log", sa.JSON(), nullable=True))
    op.add_column("publish_jobs", sa.Column("retry_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("publish_jobs", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("publish_jobs", sa.Column("parent_job_id", sa.String(length=36), nullable=True))
    op.add_column("publish_jobs", sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.add_column("publish_jobs", sa.Column("preparing_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("publish_jobs", sa.Column("publishing_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("publish_jobs", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("publish_jobs", sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("publish_jobs", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_publish_jobs_parent_job_id", "publish_jobs", ["parent_job_id"])
    op.create_index("ix_publish_jobs_updated_at", "publish_jobs", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_publish_jobs_updated_at", table_name="publish_jobs")
    op.drop_index("ix_publish_jobs_parent_job_id", table_name="publish_jobs")
    op.drop_column("publish_jobs", "updated_at")
    op.drop_column("publish_jobs", "failed_at")
    op.drop_column("publish_jobs", "published_at")
    op.drop_column("publish_jobs", "publishing_at")
    op.drop_column("publish_jobs", "preparing_at")
    op.drop_column("publish_jobs", "queued_at")
    op.drop_column("publish_jobs", "parent_job_id")
    op.drop_column("publish_jobs", "retry_count")
    op.drop_column("publish_jobs", "retry_metadata")
    op.drop_column("publish_jobs", "error_log")
    op.drop_column("publish_jobs", "external_ids")
    op.drop_column("publish_jobs", "provider_response")
    op.drop_column("publish_jobs", "request_payload")
    op.alter_column("publish_jobs", "status", server_default="scheduled")

    op.drop_index("ix_channel_plans_updated_at", table_name="channel_plans")
    op.drop_index("ix_channel_plans_parent_plan_id", table_name="channel_plans")
    op.drop_index("ix_channel_plans_status", table_name="channel_plans")
    op.drop_index("ix_channel_plans_product_id", table_name="channel_plans")
    op.drop_index("ix_channel_plans_avatar_id", table_name="channel_plans")
    op.drop_index("ix_channel_plans_project_id", table_name="channel_plans")
    op.drop_column("channel_plans", "updated_at")
    op.drop_column("channel_plans", "completed_at")
    op.drop_column("channel_plans", "started_at")
    op.drop_column("channel_plans", "parent_plan_id")
    op.drop_column("channel_plans", "retry_count")
    op.drop_column("channel_plans", "error_message")
    op.drop_column("channel_plans", "final_plan")
    op.drop_column("channel_plans", "ranking_scores")
    op.drop_column("channel_plans", "selected_variants")
    op.drop_column("channel_plans", "request_context")
    op.drop_column("channel_plans", "status")
    op.drop_column("channel_plans", "product_id")
    op.drop_column("channel_plans", "avatar_id")
    op.drop_column("channel_plans", "project_id")

    op.drop_index("ix_optimization_runs_updated_at", table_name="optimization_runs")
    op.drop_index("ix_optimization_runs_parent_run_id", table_name="optimization_runs")
    op.drop_index("ix_optimization_runs_status", table_name="optimization_runs")
    op.drop_column("optimization_runs", "updated_at")
    op.drop_column("optimization_runs", "completed_at")
    op.drop_column("optimization_runs", "started_at")
    op.drop_column("optimization_runs", "parent_run_id")
    op.drop_column("optimization_runs", "retry_count")
    op.drop_column("optimization_runs", "error_message")
    op.drop_column("optimization_runs", "score_summary")
    op.drop_column("optimization_runs", "output_payload")
    op.drop_column("optimization_runs", "input_payload")
    op.drop_column("optimization_runs", "status")
