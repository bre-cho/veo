"""avatar_acting_profile — SQLAlchemy model for avatar cinematic acting profiles."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AvatarActingProfile(Base):
    """Persistent acting / character profile for a single avatar.

    Encodes temperament, defense mechanisms, desire axis, and all cinematic
    performance defaults that drive the Avatar Acting Engine.
    """

    __tablename__ = "avatar_acting_profile"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    avatar_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)

    # Character identity
    archetype: Mapped[str] = mapped_column(String(64), nullable=False, default="observer")
    temperament: Mapped[str] = mapped_column(String(64), nullable=False, default="calm")
    defense_mechanism: Mapped[str] = mapped_column(String(64), nullable=False, default="withdrawal")
    vulnerability_axis: Mapped[str] = mapped_column(String(64), nullable=False, default="shame")
    desire_axis: Mapped[str] = mapped_column(String(64), nullable=False, default="control")

    # Performance defaults
    baseline_energy: Mapped[str] = mapped_column(String(64), nullable=False, default="medium")
    speech_tempo: Mapped[str] = mapped_column(String(64), nullable=False, default="moderate")
    pause_style: Mapped[str] = mapped_column(String(64), nullable=False, default="measured")
    gaze_style: Mapped[str] = mapped_column(String(64), nullable=False, default="direct")
    touch_boundary: Mapped[str] = mapped_column(String(64), nullable=False, default="distant")
    reaction_style: Mapped[str] = mapped_column(String(64), nullable=False, default="controlled")

    # Extended JSONB fields for presets / overrides
    shot_grammar: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    lighting_signature: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    preferred_shots: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    forbidden_shots: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, onupdate=_now
    )
