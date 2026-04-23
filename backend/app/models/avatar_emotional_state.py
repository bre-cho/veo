"""avatar_emotional_state — SQLAlchemy model for per-scene emotional state snapshots."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AvatarEmotionalState(Base):
    """Snapshot of an avatar's emotional state at a given scene/episode checkpoint.

    Written by AvatarEmotionEngine after each scene beat is processed.
    """

    __tablename__ = "avatar_emotional_state"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    avatar_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    series_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    episode_index: Mapped[int | None] = mapped_column(nullable=True)
    scene_index: Mapped[int | None] = mapped_column(nullable=True)

    primary_emotion: Mapped[str] = mapped_column(String(64), nullable=False, default="calm")
    secondary_emotion: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tension_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    control_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    openness_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    emotional_mask: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_need: Mapped[str | None] = mapped_column(String(128), nullable=True)
    scene_goal: Mapped[str | None] = mapped_column(String(128), nullable=True)

    raw_state: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
