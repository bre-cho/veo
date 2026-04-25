"""drama_scene_state — scene-level drama state produced by the Drama Engine.

.. deprecated::
    This module is a legacy copy. Use ``app.drama.models`` instead.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DramaSceneState(Base):
    """Drama analysis of a single scene.

    Records the conflict structure, power positions, and deltas that result
    from running the Drama Engine over a scene beat.
    """

    __tablename__ = "drama_scene_state"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    scene_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    project_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    episode_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    # Conflict structure
    scene_goal: Mapped[str | None] = mapped_column(String(256), nullable=True)
    visible_conflict: Mapped[str | None] = mapped_column(Text, nullable=True)
    hidden_conflict: Mapped[str | None] = mapped_column(Text, nullable=True)
    scene_temperature: Mapped[str] = mapped_column(String(32), nullable=False, default="neutral")

    pressure_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)

    # Power positions
    dominant_character_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    threatened_character_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    emotional_center_character_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    key_secret_in_play: Mapped[str | None] = mapped_column(Text, nullable=True)
    scene_turning_point: Mapped[str | None] = mapped_column(String(256), nullable=True)
    outcome_type: Mapped[str] = mapped_column(String(64), nullable=False, default="neutral")

    # Post-scene deltas (applied to relationships / states by update engine)
    power_shift_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    trust_shift_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    exposure_shift_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    dependency_shift_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    scene_aftertaste: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Full computed payload
    drama_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
