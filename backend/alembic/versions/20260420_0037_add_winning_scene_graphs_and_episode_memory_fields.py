"""Phase 4: winning_scene_graphs table + EpisodeMemory new fields

Revision ID: 20260420_0037
Revises: 20260420_0036
Create Date: 2026-04-20 12:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260420_0037"
down_revision = "20260420_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Phase 4.4: winning_scene_graphs table
    op.create_table(
        "winning_scene_graphs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("storyboard_id", sa.String(36), nullable=False),
        sa.Column("platform", sa.String(64), nullable=True),
        sa.Column("conversion_score", sa.Float(), nullable=False),
        sa.Column("scene_sequence", sa.JSON(), nullable=True),
        sa.Column("dependency_graph", sa.JSON(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=False), nullable=True),
    )
    op.create_index("ix_winning_scene_graphs_storyboard_id", "winning_scene_graphs", ["storyboard_id"])
    op.create_index("ix_winning_scene_graphs_platform", "winning_scene_graphs", ["platform"])
    op.create_index("ix_winning_scene_graphs_conversion_score", "winning_scene_graphs", ["conversion_score"])
    op.create_index("ix_winning_scene_graphs_recorded_at", "winning_scene_graphs", ["recorded_at"])

    # Phase 4.3: EpisodeMemory new fields
    op.add_column(
        "episode_memories",
        sa.Column("winning_scene_sequence", sa.JSON(), nullable=True),
    )
    op.add_column(
        "episode_memories",
        sa.Column("series_arc", sa.JSON(), nullable=True),
    )
    op.add_column(
        "episode_memories",
        sa.Column("character_callbacks", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("episode_memories", "character_callbacks")
    op.drop_column("episode_memories", "series_arc")
    op.drop_column("episode_memories", "winning_scene_sequence")

    op.drop_index("ix_winning_scene_graphs_recorded_at", table_name="winning_scene_graphs")
    op.drop_index("ix_winning_scene_graphs_conversion_score", table_name="winning_scene_graphs")
    op.drop_index("ix_winning_scene_graphs_platform", table_name="winning_scene_graphs")
    op.drop_index("ix_winning_scene_graphs_storyboard_id", table_name="winning_scene_graphs")
    op.drop_table("winning_scene_graphs")
