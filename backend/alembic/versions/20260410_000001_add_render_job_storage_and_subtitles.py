"""add render job storage and subtitles

Revision ID: 20260410_000001
Revises:
Create Date: 2026-04-10 20:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260410_000001"
down_revision = "20260408_0004"
branch_labels = None
depends_on = None

_TABLE = "render_jobs"

_NEW_COLUMNS = [
    sa.Column("storage_key", sa.Text(), nullable=True),
    sa.Column("thumbnail_url", sa.Text(), nullable=True),
    sa.Column("subtitle_segments", sa.JSON(), nullable=True),
    sa.Column("final_timeline", sa.JSON(), nullable=True),
]


def _existing_columns() -> set:
    bind = op.get_bind()
    return {col["name"] for col in inspect(bind).get_columns(_TABLE)}


def upgrade() -> None:
    existing = _existing_columns()
    with op.batch_alter_table(_TABLE) as batch_op:
        for col in _NEW_COLUMNS:
            if col.name not in existing:
                batch_op.add_column(col)


def downgrade() -> None:
    existing = _existing_columns()
    with op.batch_alter_table(_TABLE) as batch_op:
        for col in reversed(_NEW_COLUMNS):
            if col.name in existing:
                batch_op.drop_column(col.name)