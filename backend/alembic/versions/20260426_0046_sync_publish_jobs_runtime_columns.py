"""sync publish_jobs runtime columns

Revision ID: 20260426_0046
Revises: 20260426_0045
Create Date: 2026-04-26 04:05:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260426_0046"
down_revision = "20260426_0045"
branch_labels = None
depends_on = None


def _has_table(bind: sa.engine.Connection, table_name: str) -> bool:
    return table_name in inspect(bind).get_table_names()


def _column_names(bind: sa.engine.Connection, table_name: str) -> set[str]:
    return {col["name"] for col in inspect(bind).get_columns(table_name)}


def _index_names(bind: sa.engine.Connection, table_name: str) -> set[str]:
    return {idx["name"] for idx in inspect(bind).get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "publish_jobs"):
        return

    cols = _column_names(bind, "publish_jobs")
    with op.batch_alter_table("publish_jobs") as batch_op:
        if "signal_status" not in cols:
            batch_op.add_column(sa.Column("signal_status", sa.String(length=16), nullable=True))
        if "idempotency_key" not in cols:
            batch_op.add_column(sa.Column("idempotency_key", sa.String(length=64), nullable=True))
        if "preflight_status" not in cols:
            batch_op.add_column(sa.Column("preflight_status", sa.String(length=16), nullable=True))
        if "preflight_errors" not in cols:
            batch_op.add_column(sa.Column("preflight_errors", sa.JSON(), nullable=True))

    idx = _index_names(bind, "publish_jobs")
    if "ix_publish_jobs_signal_status" not in idx:
        op.create_index("ix_publish_jobs_signal_status", "publish_jobs", ["signal_status"], unique=False)
    if "ix_publish_jobs_idempotency_key" not in idx:
        op.create_index("ix_publish_jobs_idempotency_key", "publish_jobs", ["idempotency_key"], unique=True)
    if "ix_publish_jobs_preflight_status" not in idx:
        op.create_index("ix_publish_jobs_preflight_status", "publish_jobs", ["preflight_status"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "publish_jobs"):
        return

    idx = _index_names(bind, "publish_jobs")
    if "ix_publish_jobs_preflight_status" in idx:
        op.drop_index("ix_publish_jobs_preflight_status", table_name="publish_jobs")
    if "ix_publish_jobs_idempotency_key" in idx:
        op.drop_index("ix_publish_jobs_idempotency_key", table_name="publish_jobs")
    if "ix_publish_jobs_signal_status" in idx:
        op.drop_index("ix_publish_jobs_signal_status", table_name="publish_jobs")

    cols = _column_names(bind, "publish_jobs")
    with op.batch_alter_table("publish_jobs") as batch_op:
        for col_name in ["preflight_errors", "preflight_status", "idempotency_key", "signal_status"]:
            if col_name in cols:
                batch_op.drop_column(col_name)
