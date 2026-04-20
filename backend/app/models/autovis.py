from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Boolean, Date, DateTime, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def uuid_col() -> Any:
    return mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AvatarRole(Base):
    __tablename__ = "avatar_roles"

    id: Mapped[str] = uuid_col()
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    niche_tags: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=_now)


class AvatarDna(Base):
    __tablename__ = "avatar_dna"

    id: Mapped[str] = uuid_col()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    niche_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    market_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    owner_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    creator_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tags: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    meta: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=_now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)


class AvatarVisualDna(Base):
    __tablename__ = "avatar_visual_dna"

    id: Mapped[str] = uuid_col()
    avatar_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    skin_tone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    hair_style: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    hair_color: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    eye_color: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    outfit_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    background_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    age_range: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    gender_expression: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    accessories: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    reference_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)


class AvatarVoiceDna(Base):
    __tablename__ = "avatar_voice_dna"

    id: Mapped[str] = uuid_col()
    avatar_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    voice_profile_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    language_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    accent_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tone: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    pitch: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    speed: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    meta: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)


class AvatarMotionDna(Base):
    __tablename__ = "avatar_motion_dna"

    id: Mapped[str] = uuid_col()
    avatar_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    motion_style: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    gesture_set: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    idle_animation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lipsync_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    blink_rate: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    meta: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)


class TemplateFamily(Base):
    __tablename__ = "template_families"

    id: Mapped[str] = uuid_col()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_goal: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    niche_tags: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    market_codes: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=_now)


class TemplateRoleMap(Base):
    __tablename__ = "template_role_map"

    id: Mapped[str] = uuid_col()
    template_family_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role_id: Mapped[str] = mapped_column(String(36), nullable=False)
    fit_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)


class AvatarMarketFit(Base):
    __tablename__ = "avatar_market_fit"

    id: Mapped[str] = uuid_col()
    avatar_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    market_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    fit_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)


class AvatarTemplateFit(Base):
    __tablename__ = "avatar_template_fit"

    id: Mapped[str] = uuid_col()
    avatar_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    template_family_id: Mapped[str] = mapped_column(String(36), nullable=False)
    fit_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)


class MarketplaceItem(Base):
    __tablename__ = "marketplace_items"

    id: Mapped[str] = uuid_col()
    avatar_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    creator_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    price_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    license_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    is_free: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    download_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rating_avg: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2), nullable=True)
    rating_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tags: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=_now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)


class AvatarUsageEvent(Base):
    __tablename__ = "avatar_usage_events"

    id: Mapped[str] = uuid_col()
    avatar_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    render_job_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    meta: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=_now, index=True)


class CreatorEarning(Base):
    __tablename__ = "creator_earnings"

    id: Mapped[str] = uuid_col()
    creator_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    avatar_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    amount_usd: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    earning_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    payout_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    meta: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=_now)


class AvatarRanking(Base):
    __tablename__ = "avatar_rankings"

    id: Mapped[str] = uuid_col()
    avatar_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    rank_score: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal("0"))
    usage_count_7d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    usage_count_30d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    download_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trending_score: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal("0"))
    last_computed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class CreatorRanking(Base):
    __tablename__ = "creator_rankings"

    id: Mapped[str] = uuid_col()
    creator_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    rank_score: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal("0"))
    total_earnings_usd: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0"))
    avatar_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_computed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AvatarCollection(Base):
    __tablename__ = "avatar_collections"

    id: Mapped[str] = uuid_col()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    avatar_ids: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=_now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)


class LocalizationProfile(Base):
    __tablename__ = "localization_profiles"

    id: Mapped[str] = uuid_col()
    market_code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    country_name: Mapped[str] = mapped_column(String(120), nullable=False)
    language_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    currency_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    rtl: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    preferred_niches: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    preferred_roles: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    meta: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=_now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)


class PerformanceSnapshot(Base):
    __tablename__ = "performance_snapshots"

    id: Mapped[str] = uuid_col()
    avatar_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    views_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uses_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    downloads_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    earnings_usd: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal("0"))
    conversion_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 4), nullable=True)
    meta: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    captured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=_now)
