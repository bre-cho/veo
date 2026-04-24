from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DramaCharacterProfile(Base):
    """
    Persistent source of truth for a character's stable psychology DNA.

    Notes for integration:
    - Keep this additive. Do not overload current avatar tables until drama
      workflows prove stable.
    - `project_id` is a string on purpose in this skeleton to stay compatible
      with repos using UUIDs, ULIDs, ints, or external workspace IDs. Tighten
      the type later when wiring into the actual project model.
    """

    __tablename__ = "drama_character_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    archetype: Mapped[str] = mapped_column(String(100), index=True, nullable=False)

    public_persona: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    private_self: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outer_goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hidden_need: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    core_wound: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dominant_fear: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mask_strategy: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pressure_response: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    speech_pattern: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    movement_pattern: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    gaze_pattern: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    acting_preset_seed: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    status_default: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    dominance_baseline: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    trust_baseline: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    openness_baseline: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    volatility_baseline: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    tags: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def bootstrap_state_payload(self) -> dict[str, Any]:
        """
        Build an initial state payload from profile baselines.

        This intentionally stays lightweight so the cast service can create a
        stable state row without needing the full continuity engine yet.
        """
        return {
            "dominance_level": self.dominance_baseline,
            "trust_level": self.trust_baseline,
            "openness_level": self.openness_baseline,
            "control_level": max(0.0, min(1.0, 1.0 - self.volatility_baseline + 0.5)),
            "mask_strength": max(0.0, min(1.0, 1.0 - self.openness_baseline + 0.2)),
            "current_power_position": "neutral",
            "current_subtext": None,
        }
