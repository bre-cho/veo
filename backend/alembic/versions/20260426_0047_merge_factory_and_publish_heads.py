"""merge factory and publish runtime heads

Revision ID: 20260426_0047
Revises: 20260425_0046, 20260426_0046
Create Date: 2026-04-26 11:30:00.000000
"""

from __future__ import annotations


revision = "20260426_0047"
down_revision = ("20260425_0046", "20260426_0046")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge migration: no schema changes.
    pass


def downgrade() -> None:
    # Merge migration: no schema changes.
    pass
