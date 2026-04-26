"""sync render models with runtime schema

Revision ID: 20260426_0045
Revises: 20260424_0044
Create Date: 2026-04-26 03:55:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "20260426_0045"
down_revision = "20260424_0044"
branch_labels = None
depends_on = None


def _has_table(bind: sa.engine.Connection, table_name: str) -> bool:
    return table_name in inspect(bind).get_table_names()


def _column_names(bind: sa.engine.Connection, table_name: str) -> set[str]:
    return {col["name"] for col in inspect(bind).get_columns(table_name)}


def _index_names(bind: sa.engine.Connection, table_name: str) -> set[str]:
    return {idx["name"] for idx in inspect(bind).get_indexes(table_name)}


def _column_type_name(bind: sa.engine.Connection, table_name: str, col_name: str) -> str | None:
    for col in inspect(bind).get_columns(table_name):
        if col["name"] == col_name:
            return str(col["type"]).lower()
    return None


def upgrade() -> None:
    bind = op.get_bind()

    if _has_table(bind, "render_jobs"):
        cols = _column_names(bind, "render_jobs")
        with op.batch_alter_table("render_jobs") as batch_op:
            if "aspect_ratio" not in cols:
                batch_op.add_column(sa.Column("aspect_ratio", sa.String(length=20), nullable=False, server_default="16:9"))
            if "style_preset" not in cols:
                batch_op.add_column(sa.Column("style_preset", sa.String(length=100), nullable=True))
            if "subtitle_mode" not in cols:
                batch_op.add_column(sa.Column("subtitle_mode", sa.String(length=50), nullable=True))
            if "merge_mode" not in cols:
                batch_op.add_column(sa.Column("merge_mode", sa.String(length=50), nullable=True))
            if "error_message" not in cols:
                batch_op.add_column(sa.Column("error_message", sa.Text(), nullable=True))
            if "planned_scene_count" not in cols:
                batch_op.add_column(sa.Column("planned_scene_count", sa.Integer(), nullable=False, server_default="0"))
            if "completed_scene_count" not in cols:
                batch_op.add_column(sa.Column("completed_scene_count", sa.Integer(), nullable=False, server_default="0"))
            if "failed_scene_count" not in cols:
                batch_op.add_column(sa.Column("failed_scene_count", sa.Integer(), nullable=False, server_default="0"))
            if "output_url" not in cols:
                batch_op.add_column(sa.Column("output_url", sa.Text(), nullable=True))
            if "output_path" not in cols:
                batch_op.add_column(sa.Column("output_path", sa.Text(), nullable=True))
            if "final_timeline_json" not in cols:
                batch_op.add_column(sa.Column("final_timeline_json", sa.Text(), nullable=True))
            if "final_video_url" not in cols:
                batch_op.add_column(sa.Column("final_video_url", sa.Text(), nullable=True))
            if "final_video_path" not in cols:
                batch_op.add_column(sa.Column("final_video_path", sa.Text(), nullable=True))
            if "completed_at" not in cols:
                batch_op.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
            if "final_storage_bucket" not in cols:
                batch_op.add_column(sa.Column("final_storage_bucket", sa.String(length=255), nullable=True))
            if "final_storage_key" not in cols:
                batch_op.add_column(sa.Column("final_storage_key", sa.Text(), nullable=True))
            if "final_signed_url" not in cols:
                batch_op.add_column(sa.Column("final_signed_url", sa.Text(), nullable=True))

    if _has_table(bind, "render_scene_tasks"):
        cols = _column_names(bind, "render_scene_tasks")
        with op.batch_alter_table("render_scene_tasks") as batch_op:
            if "job_id" not in cols:
                batch_op.add_column(sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True))
            if "scene_index" not in cols:
                batch_op.add_column(sa.Column("scene_index", sa.Integer(), nullable=False, server_default="0"))
            if "request_payload_json" not in cols:
                batch_op.add_column(sa.Column("request_payload_json", sa.Text(), nullable=False, server_default="{}"))
            if "response_payload_json" not in cols:
                batch_op.add_column(sa.Column("response_payload_json", sa.Text(), nullable=True))
            if "output_video_url" not in cols:
                batch_op.add_column(sa.Column("output_video_url", sa.Text(), nullable=True))
            if "output_thumbnail_url" not in cols:
                batch_op.add_column(sa.Column("output_thumbnail_url", sa.Text(), nullable=True))
            if "local_video_path" not in cols:
                batch_op.add_column(sa.Column("local_video_path", sa.Text(), nullable=True))
            if "storage_signed_url" not in cols:
                batch_op.add_column(sa.Column("storage_signed_url", sa.Text(), nullable=True))

        cols_after = _column_names(bind, "render_scene_tasks")
        job_id_type = _column_type_name(bind, "render_scene_tasks", "job_id")
        if "job_id" in cols_after and job_id_type and "uuid" not in job_id_type:
            op.execute(
                """
                UPDATE render_scene_tasks
                SET job_id = NULL
                WHERE job_id IS NOT NULL
                  AND job_id !~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
                """
            )
            op.alter_column(
                "render_scene_tasks",
                "job_id",
                type_=postgresql.UUID(as_uuid=True),
                postgresql_using="NULLIF(job_id, '')::uuid",
                nullable=True,
            )

        if "job_id" in cols_after and "render_job_id" in cols_after:
            op.execute(
                """
                UPDATE render_scene_tasks
                SET job_id = render_job_id
                WHERE job_id IS NULL AND render_job_id IS NOT NULL
                """
            )

        idx = _index_names(bind, "render_scene_tasks")
        if "ix_render_scene_tasks_job_id" not in idx and "job_id" in cols_after:
            op.create_index("ix_render_scene_tasks_job_id", "render_scene_tasks", ["job_id"], unique=False)
        if "ix_render_scene_tasks_scene_index" not in idx and "scene_index" in cols_after:
            op.create_index("ix_render_scene_tasks_scene_index", "render_scene_tasks", ["scene_index"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()

    if _has_table(bind, "render_scene_tasks"):
        idx = _index_names(bind, "render_scene_tasks")
        if "ix_render_scene_tasks_scene_index" in idx:
            op.drop_index("ix_render_scene_tasks_scene_index", table_name="render_scene_tasks")
        if "ix_render_scene_tasks_job_id" in idx:
            op.drop_index("ix_render_scene_tasks_job_id", table_name="render_scene_tasks")

        cols = _column_names(bind, "render_scene_tasks")
        with op.batch_alter_table("render_scene_tasks") as batch_op:
            for col_name in [
                "storage_signed_url",
                "local_video_path",
                "output_thumbnail_url",
                "output_video_url",
                "response_payload_json",
                "request_payload_json",
                "scene_index",
                "job_id",
            ]:
                if col_name in cols:
                    batch_op.drop_column(col_name)

    if _has_table(bind, "render_jobs"):
        cols = _column_names(bind, "render_jobs")
        with op.batch_alter_table("render_jobs") as batch_op:
            for col_name in [
                "final_signed_url",
                "final_storage_key",
                "final_storage_bucket",
                "completed_at",
                "final_video_path",
                "final_video_url",
                "final_timeline_json",
                "output_path",
                "output_url",
                "failed_scene_count",
                "completed_scene_count",
                "planned_scene_count",
                "error_message",
                "merge_mode",
                "subtitle_mode",
                "style_preset",
                "aspect_ratio",
            ]:
                if col_name in cols:
                    batch_op.drop_column(col_name)
