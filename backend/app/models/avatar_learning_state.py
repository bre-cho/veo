"""avatar_learning_state — per-avatar adaptive policy weights and dynamic thresholds."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AvatarLearningState(Base):
    """Stores the per-avatar adaptive weight parameters that are updated by the
    PolicyAdapter as new feedback arrives.  These values are consumed by the
    tournament scoring pipeline to favour high-performing avatars dynamically.
    """

    __tablename__ = "avatar_learning_state"

    avatar_id: Mapped[str] = mapped_column(
        String(128), primary_key=True
    )

    # Adaptive policy weights (sum need not equal 1.0)
    priority_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    exploration_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    risk_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)

    # Dynamic performance thresholds (auto-tuned per context)
    dynamic_retention_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.4)
    dynamic_ctr_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.06)

    # Outcome counters
    total_outcomes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    positive_outcomes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, onupdate=_now
    )
