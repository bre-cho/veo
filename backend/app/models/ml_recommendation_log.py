"""ORM model for ML prediction / recommendation log entries."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class MlRecommendationLog(Base):
    """Logs each ML prediction made by the RenderPredictor."""

    __tablename__ = "ml_recommendation_log"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    predictor_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    fail_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    slow_render: Mapped[float | None] = mapped_column(Float, nullable=True)
    feature_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
