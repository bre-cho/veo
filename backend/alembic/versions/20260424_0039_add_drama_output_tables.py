"""add drama output tables

Revision ID: 20260424_0039
Revises: 20260424_0038
Create Date: 2026-04-24 05:20:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260424_0039"
down_revision = "20260424_0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "drama_dialogue_subtexts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("episode_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("speaker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drama_character_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drama_character_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("literal_intent", sa.Text(), nullable=True),
        sa.Column("hidden_intent", sa.Text(), nullable=True),
        sa.Column("psychological_action", sa.Text(), nullable=True),
        sa.Column("suggested_subtext", sa.Text(), nullable=True),
        sa.Column("threat_level", sa.Float(), nullable=False, server_default="0"),
        sa.Column("honesty_level", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("mask_level", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_drama_dialogue_subtexts_project_id", "drama_dialogue_subtexts", ["project_id"], unique=False)
    op.create_index("ix_drama_dialogue_subtexts_episode_id", "drama_dialogue_subtexts", ["episode_id"], unique=False)
    op.create_index("ix_drama_dialogue_subtexts_scene_id", "drama_dialogue_subtexts", ["scene_id"], unique=False)

    op.create_table(
        "drama_power_shifts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("episode_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_character_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drama_character_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_character_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drama_character_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trigger_event", sa.String(length=64), nullable=True),
        sa.Column("social_delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("emotional_delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("informational_delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("moral_delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("spatial_delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("narrative_control_delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_drama_power_shifts_project_id", "drama_power_shifts", ["project_id"], unique=False)
    op.create_index("ix_drama_power_shifts_episode_id", "drama_power_shifts", ["episode_id"], unique=False)
    op.create_index("ix_drama_power_shifts_scene_id", "drama_power_shifts", ["scene_id"], unique=False)

    op.create_table(
        "drama_blocking_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("episode_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dominant_character_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("threatened_character_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("emotional_anchor_character_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("spatial_mode", sa.String(length=64), nullable=True),
        sa.Column("distance_strategy", sa.String(length=64), nullable=True),
        sa.Column("eye_line_strategy", sa.String(length=64), nullable=True),
        sa.Column("body_orientation", sa.String(length=64), nullable=True),
        sa.Column("pressure_movement", sa.String(length=64), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("scene_id", name="uq_drama_blocking_plans_scene_id"),
    )
    op.create_index("ix_drama_blocking_plans_project_id", "drama_blocking_plans", ["project_id"], unique=False)
    op.create_index("ix_drama_blocking_plans_episode_id", "drama_blocking_plans", ["episode_id"], unique=False)
    op.create_index("ix_drama_blocking_plans_scene_id", "drama_blocking_plans", ["scene_id"], unique=False)

    op.create_table(
        "drama_camera_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("episode_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dominant_character_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("emotional_anchor_character_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("primary_shot", sa.String(length=64), nullable=True),
        sa.Column("primary_move", sa.String(length=64), nullable=True),
        sa.Column("lens_psychology_mode", sa.String(length=64), nullable=True),
        sa.Column("reveal_timing", sa.String(length=64), nullable=True),
        sa.Column("movement_strategy", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("render_bridge_tokens", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("scene_id", name="uq_drama_camera_plans_scene_id"),
    )
    op.create_index("ix_drama_camera_plans_project_id", "drama_camera_plans", ["project_id"], unique=False)
    op.create_index("ix_drama_camera_plans_episode_id", "drama_camera_plans", ["episode_id"], unique=False)
    op.create_index("ix_drama_camera_plans_scene_id", "drama_camera_plans", ["scene_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_drama_camera_plans_scene_id", table_name="drama_camera_plans")
    op.drop_index("ix_drama_camera_plans_episode_id", table_name="drama_camera_plans")
    op.drop_index("ix_drama_camera_plans_project_id", table_name="drama_camera_plans")
    op.drop_table("drama_camera_plans")

    op.drop_index("ix_drama_blocking_plans_scene_id", table_name="drama_blocking_plans")
    op.drop_index("ix_drama_blocking_plans_episode_id", table_name="drama_blocking_plans")
    op.drop_index("ix_drama_blocking_plans_project_id", table_name="drama_blocking_plans")
    op.drop_table("drama_blocking_plans")

    op.drop_index("ix_drama_power_shifts_scene_id", table_name="drama_power_shifts")
    op.drop_index("ix_drama_power_shifts_episode_id", table_name="drama_power_shifts")
    op.drop_index("ix_drama_power_shifts_project_id", table_name="drama_power_shifts")
    op.drop_table("drama_power_shifts")

    op.drop_index("ix_drama_dialogue_subtexts_scene_id", table_name="drama_dialogue_subtexts")
    op.drop_index("ix_drama_dialogue_subtexts_episode_id", table_name="drama_dialogue_subtexts")
    op.drop_index("ix_drama_dialogue_subtexts_project_id", table_name="drama_dialogue_subtexts")
    op.drop_table("drama_dialogue_subtexts")
