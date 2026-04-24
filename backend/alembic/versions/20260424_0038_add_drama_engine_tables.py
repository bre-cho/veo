"""add drama engine tables

Revision ID: 20260424_0038
Revises: 20260420_0037
Create Date: 2026-04-24 03:40:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260424_0038"
down_revision = "20260420_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "drama_character_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("archetype", sa.String(length=100), nullable=False),
        sa.Column("public_persona", sa.Text(), nullable=True),
        sa.Column("private_self", sa.Text(), nullable=True),
        sa.Column("outer_goal", sa.Text(), nullable=True),
        sa.Column("hidden_need", sa.Text(), nullable=True),
        sa.Column("core_wound", sa.Text(), nullable=True),
        sa.Column("dominant_fear", sa.Text(), nullable=True),
        sa.Column("mask_strategy", sa.Text(), nullable=True),
        sa.Column("pressure_response", sa.String(length=100), nullable=True),
        sa.Column("speech_pattern", sa.JSON(), nullable=True),
        sa.Column("movement_pattern", sa.JSON(), nullable=True),
        sa.Column("gaze_pattern", sa.JSON(), nullable=True),
        sa.Column("acting_preset_seed", sa.JSON(), nullable=True),
        sa.Column("status_default", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("dominance_baseline", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("trust_baseline", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("openness_baseline", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("volatility_baseline", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_drama_character_profiles_project_id", "drama_character_profiles", ["project_id"], unique=False)
    op.create_index("ix_drama_character_profiles_archetype", "drama_character_profiles", ["archetype"], unique=False)

    op.create_table(
        "drama_character_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drama_character_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scene_id", sa.String(length=128), nullable=True),
        sa.Column("emotional_valence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("arousal", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("control_level", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("dominance_level", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("vulnerability_level", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("trust_level", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("shame_level", sa.Float(), nullable=False, server_default="0"),
        sa.Column("anger_level", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fear_level", sa.Float(), nullable=False, server_default="0"),
        sa.Column("desire_level", sa.Float(), nullable=False, server_default="0"),
        sa.Column("openness_level", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("mask_strength", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("internal_conflict_level", sa.Float(), nullable=False, server_default="0"),
        sa.Column("goal_pressure_level", sa.Float(), nullable=False, server_default="0"),
        sa.Column("current_subtext", sa.Text(), nullable=True),
        sa.Column("current_secret_load", sa.Text(), nullable=True),
        sa.Column("current_power_position", sa.String(length=64), nullable=False, server_default="neutral"),
        sa.Column("update_reason", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_drama_character_states_character_id", "drama_character_states", ["character_id"], unique=False)
    op.create_index("ix_drama_character_states_scene_id", "drama_character_states", ["scene_id"], unique=False)

    op.create_table(
        "drama_relationship_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column(
            "source_character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drama_character_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drama_character_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relation_type", sa.String(length=64), nullable=False),
        sa.Column("intimacy_level", sa.Float(), nullable=False, server_default="0"),
        sa.Column("trust_level", sa.Float(), nullable=False, server_default="0"),
        sa.Column("dependence_level", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fear_level", sa.Float(), nullable=False, server_default="0"),
        sa.Column("resentment_level", sa.Float(), nullable=False, server_default="0"),
        sa.Column("attraction_level", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rivalry_level", sa.Float(), nullable=False, server_default="0"),
        sa.Column("dominance_source_over_target", sa.Float(), nullable=False, server_default="0"),
        sa.Column("perceived_loyalty", sa.Float(), nullable=False, server_default="0"),
        sa.Column("hidden_agenda_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("recent_betrayal_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("unresolved_tension_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("last_interaction_scene_id", sa.String(length=128), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "source_character_id", "target_character_id", name="uq_drama_relationship_edges_project_pair"),
    )
    op.create_index("ix_drama_relationship_edges_project_id", "drama_relationship_edges", ["project_id"], unique=False)
    op.create_index("ix_drama_relationship_edges_source_character_id", "drama_relationship_edges", ["source_character_id"], unique=False)
    op.create_index("ix_drama_relationship_edges_target_character_id", "drama_relationship_edges", ["target_character_id"], unique=False)

    op.create_table(
        "drama_scene_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("episode_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scene_goal", sa.Text(), nullable=True),
        sa.Column("visible_conflict", sa.Text(), nullable=True),
        sa.Column("hidden_conflict", sa.Text(), nullable=True),
        sa.Column("scene_temperature", sa.Float(), nullable=False, server_default="0"),
        sa.Column("pressure_level", sa.Float(), nullable=False, server_default="0"),
        sa.Column("dominant_character_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("emotional_center_character_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("threatened_character_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("turning_point", sa.Text(), nullable=True),
        sa.Column("outcome_type", sa.String(length=64), nullable=True),
        sa.Column("power_shift_delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("trust_shift_delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("exposure_shift_delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("dependency_shift_delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("analysis_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("continuity_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("compile_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("scene_id", name="uq_drama_scene_states_scene_id"),
    )
    op.create_index("ix_drama_scene_states_project_id", "drama_scene_states", ["project_id"], unique=False)
    op.create_index("ix_drama_scene_states_episode_id", "drama_scene_states", ["episode_id"], unique=False)
    op.create_index("ix_drama_scene_states_scene_id", "drama_scene_states", ["scene_id"], unique=False)
    op.create_index("ix_drama_scene_states_outcome_type", "drama_scene_states", ["outcome_type"], unique=False)

    op.create_table(
        "drama_memory_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("episode_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drama_character_profiles.id"),
            nullable=False,
        ),
        sa.Column(
            "related_character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drama_character_profiles.id"),
            nullable=True,
        ),
        sa.Column("source_scene_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("meaning_label", sa.String(length=128), nullable=True),
        sa.Column("recall_trigger", sa.String(length=128), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("emotional_weight", sa.Float(), nullable=False, server_default="0"),
        sa.Column("trust_impact", sa.Float(), nullable=False, server_default="0"),
        sa.Column("shame_impact", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fear_impact", sa.Float(), nullable=False, server_default="0"),
        sa.Column("dominance_impact", sa.Float(), nullable=False, server_default="0"),
        sa.Column("persistence_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("decay_rate", sa.Float(), nullable=False, server_default="0.05"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_drama_memory_traces_project_id", "drama_memory_traces", ["project_id"], unique=False)
    op.create_index("ix_drama_memory_traces_episode_id", "drama_memory_traces", ["episode_id"], unique=False)
    op.create_index("ix_drama_memory_traces_character_id", "drama_memory_traces", ["character_id"], unique=False)
    op.create_index("ix_drama_memory_traces_related_character_id", "drama_memory_traces", ["related_character_id"], unique=False)
    op.create_index("ix_drama_memory_traces_source_scene_id", "drama_memory_traces", ["source_scene_id"], unique=False)
    op.create_index("ix_drama_memory_traces_event_type", "drama_memory_traces", ["event_type"], unique=False)

    op.create_table(
        "drama_arc_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("episode_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drama_character_profiles.id"),
            nullable=False,
        ),
        sa.Column("arc_name", sa.String(length=128), nullable=False),
        sa.Column("arc_stage", sa.String(length=64), nullable=False, server_default="mask_stable"),
        sa.Column("false_belief", sa.Text(), nullable=True),
        sa.Column("pressure_index", sa.Float(), nullable=False, server_default="0"),
        sa.Column("transformation_index", sa.Float(), nullable=False, server_default="0"),
        sa.Column("collapse_risk", sa.Float(), nullable=False, server_default="0"),
        sa.Column("mask_break_level", sa.Float(), nullable=False, server_default="0"),
        sa.Column("truth_acceptance_level", sa.Float(), nullable=False, server_default="0"),
        sa.Column("relation_entanglement_index", sa.Float(), nullable=False, server_default="0"),
        sa.Column("latest_scene_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_drama_arc_progress_project_id", "drama_arc_progress", ["project_id"], unique=False)
    op.create_index("ix_drama_arc_progress_episode_id", "drama_arc_progress", ["episode_id"], unique=False)
    op.create_index("ix_drama_arc_progress_character_id", "drama_arc_progress", ["character_id"], unique=False)
    op.create_index("ix_drama_arc_progress_arc_stage", "drama_arc_progress", ["arc_stage"], unique=False)
    op.create_index("ix_drama_arc_progress_latest_scene_id", "drama_arc_progress", ["latest_scene_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_drama_arc_progress_latest_scene_id", table_name="drama_arc_progress")
    op.drop_index("ix_drama_arc_progress_arc_stage", table_name="drama_arc_progress")
    op.drop_index("ix_drama_arc_progress_character_id", table_name="drama_arc_progress")
    op.drop_index("ix_drama_arc_progress_episode_id", table_name="drama_arc_progress")
    op.drop_index("ix_drama_arc_progress_project_id", table_name="drama_arc_progress")
    op.drop_table("drama_arc_progress")

    op.drop_index("ix_drama_memory_traces_event_type", table_name="drama_memory_traces")
    op.drop_index("ix_drama_memory_traces_source_scene_id", table_name="drama_memory_traces")
    op.drop_index("ix_drama_memory_traces_related_character_id", table_name="drama_memory_traces")
    op.drop_index("ix_drama_memory_traces_character_id", table_name="drama_memory_traces")
    op.drop_index("ix_drama_memory_traces_episode_id", table_name="drama_memory_traces")
    op.drop_index("ix_drama_memory_traces_project_id", table_name="drama_memory_traces")
    op.drop_table("drama_memory_traces")

    op.drop_index("ix_drama_scene_states_outcome_type", table_name="drama_scene_states")
    op.drop_index("ix_drama_scene_states_scene_id", table_name="drama_scene_states")
    op.drop_index("ix_drama_scene_states_episode_id", table_name="drama_scene_states")
    op.drop_index("ix_drama_scene_states_project_id", table_name="drama_scene_states")
    op.drop_table("drama_scene_states")

    op.drop_index("ix_drama_relationship_edges_target_character_id", table_name="drama_relationship_edges")
    op.drop_index("ix_drama_relationship_edges_source_character_id", table_name="drama_relationship_edges")
    op.drop_index("ix_drama_relationship_edges_project_id", table_name="drama_relationship_edges")
    op.drop_table("drama_relationship_edges")

    op.drop_index("ix_drama_character_states_scene_id", table_name="drama_character_states")
    op.drop_index("ix_drama_character_states_character_id", table_name="drama_character_states")
    op.drop_table("drama_character_states")

    op.drop_index("ix_drama_character_profiles_archetype", table_name="drama_character_profiles")
    op.drop_index("ix_drama_character_profiles_project_id", table_name="drama_character_profiles")
    op.drop_table("drama_character_profiles")
