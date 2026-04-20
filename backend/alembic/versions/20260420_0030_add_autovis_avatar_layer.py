"""Add Autovis avatar commerce layer

Revision ID: 20260420_0030
Revises: 20260418_0029
Create Date: 2026-04-20 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260420_0030"
down_revision = "20260418_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "avatar_roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("niche_tags", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_avatar_roles_name", "avatar_roles", ["name"])

    op.create_table(
        "avatar_dna",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role_id", sa.String(36), sa.ForeignKey("avatar_roles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("niche_code", sa.String(80), nullable=True),
        sa.Column("market_code", sa.String(20), nullable=True),
        sa.Column("owner_user_id", sa.String(36), nullable=True),
        sa.Column("creator_id", sa.String(36), nullable=True),
        sa.Column("is_published", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_featured", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("tags", sa.JSON, nullable=True),
        sa.Column("meta", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_avatar_dna_niche_code", "avatar_dna", ["niche_code"])
    op.create_index("ix_avatar_dna_market_code", "avatar_dna", ["market_code"])
    op.create_index("ix_avatar_dna_creator_id", "avatar_dna", ["creator_id"])
    op.create_index("ix_avatar_dna_is_published", "avatar_dna", ["is_published"])

    op.create_table(
        "avatar_visual_dna",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("avatar_id", sa.String(36), sa.ForeignKey("avatar_dna.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skin_tone", sa.String(50), nullable=True),
        sa.Column("hair_style", sa.String(100), nullable=True),
        sa.Column("hair_color", sa.String(50), nullable=True),
        sa.Column("eye_color", sa.String(50), nullable=True),
        sa.Column("outfit_code", sa.String(100), nullable=True),
        sa.Column("background_code", sa.String(100), nullable=True),
        sa.Column("age_range", sa.String(20), nullable=True),
        sa.Column("gender_expression", sa.String(50), nullable=True),
        sa.Column("accessories", sa.JSON, nullable=True),
        sa.Column("reference_image_url", sa.Text, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_avatar_visual_dna_avatar_id", "avatar_visual_dna", ["avatar_id"])

    op.create_table(
        "avatar_voice_dna",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("avatar_id", sa.String(36), sa.ForeignKey("avatar_dna.id", ondelete="CASCADE"), nullable=False),
        sa.Column("voice_profile_id", sa.String(36), sa.ForeignKey("voice_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("language_code", sa.String(20), nullable=True),
        sa.Column("accent_code", sa.String(50), nullable=True),
        sa.Column("tone", sa.String(80), nullable=True),
        sa.Column("pitch", sa.String(20), nullable=True),
        sa.Column("speed", sa.String(20), nullable=True),
        sa.Column("meta", sa.JSON, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_avatar_voice_dna_avatar_id", "avatar_voice_dna", ["avatar_id"])

    op.create_table(
        "avatar_motion_dna",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("avatar_id", sa.String(36), sa.ForeignKey("avatar_dna.id", ondelete="CASCADE"), nullable=False),
        sa.Column("motion_style", sa.String(100), nullable=True),
        sa.Column("gesture_set", sa.String(100), nullable=True),
        sa.Column("idle_animation", sa.String(100), nullable=True),
        sa.Column("lipsync_mode", sa.String(50), nullable=True),
        sa.Column("blink_rate", sa.String(20), nullable=True),
        sa.Column("meta", sa.JSON, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_avatar_motion_dna_avatar_id", "avatar_motion_dna", ["avatar_id"])

    op.create_table(
        "template_families",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("content_goal", sa.String(120), nullable=True),
        sa.Column("niche_tags", sa.JSON, nullable=True),
        sa.Column("market_codes", sa.JSON, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_template_families_content_goal", "template_families", ["content_goal"])

    op.create_table(
        "template_role_map",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("template_family_id", sa.String(36), sa.ForeignKey("template_families.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", sa.String(36), sa.ForeignKey("avatar_roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fit_score", sa.Numeric(5, 2), nullable=True),
    )
    op.create_index("ix_template_role_map_family", "template_role_map", ["template_family_id"])

    op.create_table(
        "avatar_market_fit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("avatar_id", sa.String(36), sa.ForeignKey("avatar_dna.id", ondelete="CASCADE"), nullable=False),
        sa.Column("market_code", sa.String(20), nullable=False),
        sa.Column("fit_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_avatar_market_fit_avatar", "avatar_market_fit", ["avatar_id"])
    op.create_index("ix_avatar_market_fit_market", "avatar_market_fit", ["market_code"])

    op.create_table(
        "avatar_template_fit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("avatar_id", sa.String(36), sa.ForeignKey("avatar_dna.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_family_id", sa.String(36), sa.ForeignKey("template_families.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fit_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_avatar_template_fit_avatar", "avatar_template_fit", ["avatar_id"])

    op.create_table(
        "marketplace_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("avatar_id", sa.String(36), sa.ForeignKey("avatar_dna.id", ondelete="CASCADE"), nullable=False),
        sa.Column("creator_id", sa.String(36), nullable=True),
        sa.Column("price_usd", sa.Numeric(10, 2), nullable=True),
        sa.Column("license_type", sa.String(80), nullable=True),
        sa.Column("is_free", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("download_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("view_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("rating_avg", sa.Numeric(3, 2), nullable=True),
        sa.Column("rating_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tags", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_marketplace_items_avatar_id", "marketplace_items", ["avatar_id"])
    op.create_index("ix_marketplace_items_creator_id", "marketplace_items", ["creator_id"])
    op.create_index("ix_marketplace_items_is_active", "marketplace_items", ["is_active"])

    op.create_table(
        "avatar_usage_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("avatar_id", sa.String(36), sa.ForeignKey("avatar_dna.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("render_job_id", sa.String(36), nullable=True),
        sa.Column("meta", sa.JSON, nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_avatar_usage_events_avatar_id", "avatar_usage_events", ["avatar_id"])
    op.create_index("ix_avatar_usage_events_user_id", "avatar_usage_events", ["user_id"])
    op.create_index("ix_avatar_usage_events_occurred_at", "avatar_usage_events", ["occurred_at"])

    op.create_table(
        "creator_earnings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("creator_id", sa.String(36), nullable=False),
        sa.Column("avatar_id", sa.String(36), sa.ForeignKey("avatar_dna.id", ondelete="SET NULL"), nullable=True),
        sa.Column("amount_usd", sa.Numeric(12, 4), nullable=False),
        sa.Column("earning_type", sa.String(80), nullable=True),
        sa.Column("period_start", sa.Date, nullable=True),
        sa.Column("period_end", sa.Date, nullable=True),
        sa.Column("payout_status", sa.String(40), nullable=False, server_default="pending"),
        sa.Column("meta", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_creator_earnings_creator_id", "creator_earnings", ["creator_id"])
    op.create_index("ix_creator_earnings_avatar_id", "creator_earnings", ["avatar_id"])

    op.create_table(
        "avatar_rankings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("avatar_id", sa.String(36), sa.ForeignKey("avatar_dna.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("rank_score", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("usage_count_7d", sa.Integer, nullable=False, server_default="0"),
        sa.Column("usage_count_30d", sa.Integer, nullable=False, server_default="0"),
        sa.Column("download_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("trending_score", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("last_computed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_avatar_rankings_rank_score", "avatar_rankings", ["rank_score"])
    op.create_index("ix_avatar_rankings_trending_score", "avatar_rankings", ["trending_score"])

    op.create_table(
        "creator_rankings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("creator_id", sa.String(36), nullable=False, unique=True),
        sa.Column("rank_score", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("total_earnings_usd", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("avatar_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_computed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_creator_rankings_creator_id", "creator_rankings", ["creator_id"])
    op.create_index("ix_creator_rankings_rank_score", "creator_rankings", ["rank_score"])

    op.create_table(
        "avatar_collections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("owner_user_id", sa.String(36), nullable=True),
        sa.Column("avatar_ids", sa.JSON, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_avatar_collections_owner_user_id", "avatar_collections", ["owner_user_id"])

    op.create_table(
        "localization_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("market_code", sa.String(20), nullable=False, unique=True),
        sa.Column("country_name", sa.String(120), nullable=False),
        sa.Column("language_code", sa.String(20), nullable=True),
        sa.Column("currency_code", sa.String(10), nullable=True),
        sa.Column("timezone", sa.String(80), nullable=True),
        sa.Column("rtl", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("preferred_niches", sa.JSON, nullable=True),
        sa.Column("preferred_roles", sa.JSON, nullable=True),
        sa.Column("meta", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_localization_profiles_market_code", "localization_profiles", ["market_code"])

    op.create_table(
        "performance_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("avatar_id", sa.String(36), sa.ForeignKey("avatar_dna.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("views_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("uses_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("downloads_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("earnings_usd", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("conversion_rate", sa.Numeric(7, 4), nullable=True),
        sa.Column("meta", sa.JSON, nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_performance_snapshots_avatar_id", "performance_snapshots", ["avatar_id"])
    op.create_index("ix_performance_snapshots_snapshot_date", "performance_snapshots", ["snapshot_date"])


def downgrade() -> None:
    op.drop_table("performance_snapshots")
    op.drop_table("localization_profiles")
    op.drop_table("avatar_collections")
    op.drop_table("creator_rankings")
    op.drop_table("avatar_rankings")
    op.drop_table("creator_earnings")
    op.drop_table("avatar_usage_events")
    op.drop_table("marketplace_items")
    op.drop_table("avatar_template_fit")
    op.drop_table("avatar_market_fit")
    op.drop_table("template_role_map")
    op.drop_table("template_families")
    op.drop_table("avatar_motion_dna")
    op.drop_table("avatar_voice_dna")
    op.drop_table("avatar_visual_dna")
    op.drop_table("avatar_dna")
    op.drop_table("avatar_roles")
