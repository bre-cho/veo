"""avatar_anomaly_event — records detected metric anomalies per avatar."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AvatarAnomalyEvent(Base):
    """Written by AvatarAnomalyDetector whenever an anomaly is identified in
    post-publish metrics for an avatar.
    """

    __tablename__ = "avatar_anomaly_event"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    avatar_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    anomaly_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # retention_drop|ctr_drop|continuity_break
    severity: Mapped[str] = mapped_column(
        String(16), nullable=False, default="medium"
    )  # low|medium|high|critical
    retention: Mapped[float | None] = mapped_column(Float, nullable=True)
    ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    continuity_health: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_retention: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    project_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
