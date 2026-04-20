"""Add creator profiles and avatar moderation status

Revision ID: 20260420_0031
Revises: 20260420_0030
Create Date: 2026-04-20 03:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260420_0031"
down_revision = "20260420_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "creator_profiles",
        sa.Column("creator_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("market_code", sa.String(length=32), nullable=True),
        sa.PrimaryKeyConstraint("creator_id"),
    )
    op.create_index("ix_creator_profiles_user_id", "creator_profiles", ["user_id"])
    op.create_index("ix_creator_profiles_market_code", "creator_profiles", ["market_code"])

    op.add_column(
        "avatar_dna",
        sa.Column("moderation_status", sa.String(length=32), nullable=False, server_default="pending"),
    )
    op.create_index("ix_avatar_dna_moderation_status", "avatar_dna", ["moderation_status"])


def downgrade() -> None:
    op.drop_index("ix_avatar_dna_moderation_status", table_name="avatar_dna")
    op.drop_column("avatar_dna", "moderation_status")

    op.drop_index("ix_creator_profiles_market_code", table_name="creator_profiles")
    op.drop_index("ix_creator_profiles_user_id", table_name="creator_profiles")
    op.drop_table("creator_profiles")
