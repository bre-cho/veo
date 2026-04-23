"""drama_character_state — per-scene mutable state for a drama character."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DramaCharacterState(Base):
    """Mutable emotional / power state for a character at a specific scene.

    Written by the Inner State Update Engine after each scene resolves.
    """

    __tablename__ = "drama_character_state"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    character_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    project_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    scene_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    episode_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    # Emotional dimensions
    emotional_valence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    arousal: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    control_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    dominance_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    vulnerability_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)
    trust_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    shame_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    anger_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fear_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    desire_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)

    # Mask and openness
    mask_strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    openness_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)

    # Scene dynamics
    internal_conflict_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    goal_pressure_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    current_subtext: Mapped[str | None] = mapped_column(String(256), nullable=True)
    current_secret_load: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_power_position: Mapped[str] = mapped_column(String(64), nullable=False, default="neutral")

    updated_from_previous_scene: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_state: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
