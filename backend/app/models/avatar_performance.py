"""avatar_performance — SQLAlchemy model for per-run avatar performance records."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AvatarPerformance(Base):
    """One performance record per avatar × publish run.

    Written by the feedback loop after publish metrics are available.
    Read by AvatarMemoryService to supply scoring context for the next
    selection cycle.
    """

    __tablename__ = "avatar_performance"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    avatar_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    market_code: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    content_goal: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    topic_class: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    template_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    retention_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    engagement_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    series_follow_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
