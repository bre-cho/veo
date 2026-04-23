"""avatar_context_baseline — EWMA performance baseline per (topic, template, platform) context."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AvatarContextBaseline(Base):
    """Stores exponentially-weighted moving averages (EWMA) of key metrics for a
    given (topic_signature, template_family, platform) context.

    Used by the adaptive learning engine to compare incoming metrics against
    the running baseline and detect anomalies.
    """

    __tablename__ = "avatar_context_baseline"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    topic_signature: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    template_family: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    platform: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    ctr_ewma: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    retention_ewma: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    watch_time_ewma: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    conversion_ewma: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, onupdate=_now
    )
