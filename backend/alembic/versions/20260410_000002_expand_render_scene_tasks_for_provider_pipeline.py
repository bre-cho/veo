"""expand render scene tasks for provider pipeline

Revision ID: 20260410_000002
Revises: 20260410_000001
Create Date: 2026-04-10 20:20:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260410_000002"
down_revision = "20260410_000001"
branch_labels = None
depends_on = None

_TABLE = "render_scene_tasks"

_NEW_COLUMNS = [
    sa.Column("title", sa.String(length=255), nullable=True),
    sa.Column("script_text", sa.Text(), nullable=True),
    sa.Column("provider_target_duration_sec", sa.Float(), nullable=True),
    sa.Column("target_duration_sec", sa.Float(), nullable=True),
    sa.Column("provider_mode", sa.String(length=50), nullable=True),
    sa.Column("source_scene_index", sa.Integer(), nullable=True),
    sa.Column("visual_prompt", sa.Text(), nullable=True),
    sa.Column("start_image_url", sa.Text(), nullable=True),
    sa.Column("end_image_url", sa.Text(), nullable=True),
    sa.Column("provider_task_id", sa.String(length=255), nullable=True),
    sa.Column("provider_operation_name", sa.String(length=255), nullable=True),
    sa.Column("provider_payload", sa.JSON(), nullable=True),
    sa.Column("output_url", sa.Text(), nullable=True),
    sa.Column("output_path", sa.Text(), nullable=True),
    sa.Column("error_message", sa.Text(), nullable=True),
    sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
]


def _existing_columns() -> set:
    bind = op.get_bind()
    return {col["name"] for col in inspect(bind).get_columns(_TABLE)}


def _existing_indexes() -> set:
    bind = op.get_bind()
    return {idx["name"] for idx in inspect(bind).get_indexes(_TABLE)}


def upgrade() -> None:
    existing = _existing_columns()
    with op.batch_alter_table(_TABLE) as batch_op:
        for col in _NEW_COLUMNS:
            if col.name not in existing:
                batch_op.add_column(col)

    existing_idx = _existing_indexes()
    if "ix_render_scene_tasks_provider_task_id" not in existing_idx:
        op.create_index("ix_render_scene_tasks_provider_task_id", _TABLE, ["provider_task_id"])
    if "ix_render_scene_tasks_provider_operation_name" not in existing_idx:
        op.create_index("ix_render_scene_tasks_provider_operation_name", _TABLE, ["provider_operation_name"])


def downgrade() -> None:
    existing_idx = _existing_indexes()
    if "ix_render_scene_tasks_provider_operation_name" in existing_idx:
        op.drop_index("ix_render_scene_tasks_provider_operation_name", table_name=_TABLE)
    if "ix_render_scene_tasks_provider_task_id" in existing_idx:
        op.drop_index("ix_render_scene_tasks_provider_task_id", table_name=_TABLE)

    existing = _existing_columns()
    with op.batch_alter_table(_TABLE) as batch_op:
        for col in reversed(_NEW_COLUMNS):
            if col.name in existing:
                batch_op.drop_column(col.name)