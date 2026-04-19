"""add provider_status_raw nullable

Revision ID: 20260410_0005
Revises: 20260408_0004
Create Date: 2026-04-10 10:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260410_0005"
down_revision = "20260408_0004"
branch_labels = None
depends_on = None

_TABLE = "render_scene_tasks"
_COLUMN = "provider_status_raw"


def upgrade() -> None:
    bind = op.get_bind()
    existing = {col["name"] for col in inspect(bind).get_columns(_TABLE)}
    if _COLUMN not in existing:
        op.add_column(_TABLE, sa.Column(_COLUMN, sa.String(length=128), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    existing = {col["name"] for col in inspect(bind).get_columns(_TABLE)}
    if _COLUMN in existing:
        op.drop_column(_TABLE, _COLUMN)