from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260408_0003"
down_revision = "20260408_0002"
branch_labels = None
depends_on = None

_TABLE = "render_scene_tasks"

_NEW_COLUMNS = [
    sa.Column("provider_model", sa.String(length=128), nullable=True),
    sa.Column("provider_region", sa.String(length=64), nullable=True),
    sa.Column("provider_request_id", sa.String(length=255), nullable=True),
    sa.Column("provider_status_raw", sa.String(length=128), nullable=True),
    sa.Column("provider_callback_url", sa.Text(), nullable=True),
    sa.Column("submitted_at", sa.DateTime(), nullable=True),
    sa.Column("started_at", sa.DateTime(), nullable=True),
    sa.Column("finished_at", sa.DateTime(), nullable=True),
    sa.Column("last_polled_at", sa.DateTime(), nullable=True),
    sa.Column("last_callback_at", sa.DateTime(), nullable=True),
    sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("poll_fallback_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    sa.Column("output_metadata_json", sa.Text(), nullable=True),
    sa.Column("failure_code", sa.String(length=128), nullable=True),
    sa.Column("failure_category", sa.String(length=64), nullable=True),
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