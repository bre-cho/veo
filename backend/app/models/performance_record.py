from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PerformanceRecord(Base):
    """DB-backed performance record for the learning engine.

    Mirrors the JSON schema of ``PerformanceLearningEngine`` but adds
    ``platform`` and ``market_code`` columns for platform/locale filtering
    and stores ``recorded_at`` as a real ``DateTime`` column to enable
    time-decay queries.
    """

    __tablename__ = "performance_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    video_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    hook_pattern: Mapped[str] = mapped_column(String(256), nullable=False)
    cta_pattern: Mapped[str] = mapped_column(String(256), nullable=False)
    template_family: Mapped[str] = mapped_column(String(256), nullable=False)
    conversion_score: Mapped[float] = mapped_column(Float, nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    click_through_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    platform: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    market_code: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )
