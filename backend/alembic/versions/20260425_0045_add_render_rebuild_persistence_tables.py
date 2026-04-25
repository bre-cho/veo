"""add render_rebuild_audit_logs and render_rebuild_idempotency_keys tables

Revision ID: 20260425_0045
Revises: 20260424_0044
Create Date: 2026-04-25 12:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260425_0045"
down_revision = "20260424_0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "render_rebuild_audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(64), nullable=False, index=True),
        sa.Column("event", sa.String(64), nullable=False, index=True),
        sa.Column("project_id", sa.String(64), nullable=True, index=True),
        sa.Column("episode_id", sa.String(64), nullable=True),
        sa.Column("changed_scene_id", sa.String(64), nullable=True),
        sa.Column("selected_strategy", sa.String(64), nullable=True),
        sa.Column("extras_json", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False, index=True),
    )
    op.create_table(
        "render_rebuild_idempotency_keys",
        sa.Column("idempotency_key", sa.String(64), primary_key=True),
        sa.Column("job_id", sa.String(64), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False, index=True),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("render_rebuild_idempotency_keys")
    op.drop_table("render_rebuild_audit_logs")
