"""add factory pipeline tables

Revision ID: 20260425_0046
Revises: 20260425_0045
Create Date: 2026-04-25 18:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260425_0046"
down_revision = "20260425_0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "factory_runs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("trace_id", sa.String(128), nullable=True, index=True),
        sa.Column("project_id", sa.String(64), nullable=True, index=True),
        sa.Column("input_type", sa.String(32), nullable=False, server_default="topic"),
        sa.Column("input_topic", sa.Text(), nullable=True),
        sa.Column("input_script", sa.Text(), nullable=True),
        sa.Column("input_avatar_id", sa.String(64), nullable=True),
        sa.Column("input_series_id", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending", index=True),
        sa.Column("current_stage", sa.String(64), nullable=False, server_default="INTAKE", index=True),
        sa.Column("percent_complete", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("render_job_id", sa.String(64), nullable=True, index=True),
        sa.Column("output_video_url", sa.Text(), nullable=True),
        sa.Column("output_thumbnail_url", sa.Text(), nullable=True),
        sa.Column("seo_title", sa.String(255), nullable=True),
        sa.Column("seo_description", sa.Text(), nullable=True),
        sa.Column("publish_payload_json", sa.Text(), nullable=True),
        sa.Column("blocking_reason", sa.Text(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("budget_cents", sa.Integer(), nullable=True),
        sa.Column("policy_mode", sa.String(32), nullable=False, server_default="production"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "factory_run_stages",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("run_id", sa.String(64), nullable=False, index=True),
        sa.Column("stage_name", sa.String(64), nullable=False, index=True),
        sa.Column("stage_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "factory_quality_gates",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("run_id", sa.String(64), nullable=False, index=True),
        sa.Column("stage_name", sa.String(64), nullable=False, index=True),
        sa.Column("gate_name", sa.String(64), nullable=False),
        sa.Column("result", sa.String(32), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("threshold", sa.Integer(), nullable=True),
        sa.Column("action_taken", sa.String(32), nullable=False, server_default="none"),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "factory_memory_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("run_id", sa.String(64), nullable=False, index=True),
        sa.Column("memory_type", sa.String(64), nullable=False, index=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "factory_metric_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("run_id", sa.String(64), nullable=False, index=True),
        sa.Column("stage_name", sa.String(64), nullable=False, index=True),
        sa.Column("metric_name", sa.String(128), nullable=False),
        sa.Column("metric_value", sa.String(255), nullable=True),
        sa.Column("unit", sa.String(32), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "factory_incidents",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("run_id", sa.String(64), nullable=False, index=True),
        sa.Column("stage_name", sa.String(64), nullable=True, index=True),
        sa.Column("severity", sa.String(32), nullable=False, server_default="error"),
        sa.Column("incident_type", sa.String(64), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("factory_incidents")
    op.drop_table("factory_metric_events")
    op.drop_table("factory_memory_events")
    op.drop_table("factory_quality_gates")
    op.drop_table("factory_run_stages")
    op.drop_table("factory_runs")
