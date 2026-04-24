from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DramaCharacterState(Base):
    """
    Scene-local or latest-known mutable emotional state for a character.

    A row may represent:
    - the bootstrap state (scene_id NULL)
    - the latest state after a scene
    - a recomputed state during continuity rebuild
    """

    __tablename__ = "drama_character_states"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drama_character_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    scene_id: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)

    emotional_valence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    arousal: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    control_level: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    dominance_level: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    vulnerability_level: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    trust_level: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    shame_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    anger_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    fear_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    desire_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    openness_level: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    mask_strength: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    internal_conflict_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    goal_pressure_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    current_subtext: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    current_secret_load: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    current_power_position: Mapped[str] = mapped_column(String(64), default="neutral", nullable=False)
    update_reason: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    character: Mapped["DramaCharacterProfile"] = relationship("DramaCharacterProfile", backref="state_rows")
