"""avatar_match_result — per-avatar result within a tournament run."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AvatarMatchResult(Base):
    """One row per avatar evaluated in a tournament run.

    Stores both the predicted scores at selection time and the actual
    performance metrics observed after publish.
    """

    __tablename__ = "avatar_match_result"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tournament_run_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    avatar_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    template_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    topic_signature: Mapped[str | None] = mapped_column(String(256), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # --- Predicted scores at selection time ---
    predicted_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    predicted_ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_retention: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_conversion: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Actual performance after publish ---
    actual_ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_retention: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_watch_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_conversion: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_publish_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Tournament outcome ---
    fitness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    result_label: Mapped[str] = mapped_column(
        String(32), nullable=False, default="neutral"
    )  # winner|neutral|loser|rollback_candidate
    selection_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    was_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    was_exploration: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, onupdate=_now
    )
