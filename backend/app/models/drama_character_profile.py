"""drama_character_profile — SQLAlchemy model for a drama character's fixed DNA.

.. deprecated::
    This module is a legacy copy. Use ``app.drama.models`` instead.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DramaCharacterProfile(Base):
    """Persistent character DNA for the Multi-Character Drama Engine.

    These fields are fixed per character across an entire project/series.
    State that changes per-scene lives in ``DramaCharacterState``.
    """

    __tablename__ = "drama_character_profile"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    avatar_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    archetype: Mapped[str] = mapped_column(String(64), nullable=False, default="observer")

    # Public/private persona split
    public_persona: Mapped[str | None] = mapped_column(Text, nullable=True)
    private_self: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Motivation layer
    outer_goal: Mapped[str | None] = mapped_column(String(256), nullable=True)
    hidden_need: Mapped[str | None] = mapped_column(String(256), nullable=True)
    core_wound: Mapped[str | None] = mapped_column(String(256), nullable=True)
    dominant_fear: Mapped[str | None] = mapped_column(String(256), nullable=True)
    mask_strategy: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pressure_response: Mapped[str] = mapped_column(String(64), nullable=False, default="withdrawal")

    # Performance defaults
    speech_pattern: Mapped[str | None] = mapped_column(String(128), nullable=True)
    movement_pattern: Mapped[str | None] = mapped_column(String(128), nullable=True)
    gaze_pattern: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tempo_default: Mapped[str] = mapped_column(String(64), nullable=False, default="moderate")

    # Baseline relational disposition
    attachment_style: Mapped[str] = mapped_column(String(64), nullable=False, default="secure")
    dominance_baseline: Mapped[float] = mapped_column(nullable=False, default=0.5)
    trust_baseline: Mapped[float] = mapped_column(nullable=False, default=0.5)
    openness_baseline: Mapped[float] = mapped_column(nullable=False, default=0.5)
    volatility_baseline: Mapped[float] = mapped_column(nullable=False, default=0.3)

    acting_preset_seed: Mapped[str] = mapped_column(String(64), nullable=False, default="mentor")
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, onupdate=_now
    )
