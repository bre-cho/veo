"""drama_blocking_plan — physical/spatial blocking plan derived from drama state."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DramaBlockingPlan(Base):
    """Spatial blocking plan for a character in a scene.

    Blocking is derived from power position and relation type, not aesthetics.
    Each record covers one character for one scene.
    Index: (scene_id), (character_id).
    """

    __tablename__ = "drama_blocking_plan"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    scene_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    project_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    character_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)

    # Physical positioning
    spatial_position: Mapped[str | None] = mapped_column(String(128), nullable=True)
    facing_direction: Mapped[str | None] = mapped_column(String(64), nullable=True)
    distance_from_target: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Movement behaviour
    movement_cue: Mapped[str | None] = mapped_column(String(128), nullable=True)
    distance_change: Mapped[str | None] = mapped_column(String(64), nullable=True)
    body_angle: Mapped[str | None] = mapped_column(String(64), nullable=True)
    who_steps_first: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    who_turns_away_first: Mapped[str | None] = mapped_column(String(36), nullable=True)
    who_sits: Mapped[str | None] = mapped_column(String(36), nullable=True)
    who_controls_exit: Mapped[str | None] = mapped_column(String(36), nullable=True)
    who_occupies_center: Mapped[str | None] = mapped_column(String(36), nullable=True)
    who_is_cornered: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Camera hints
    camera_angle_preference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    shot_type_preference: Mapped[str | None] = mapped_column(String(64), nullable=True)

    drama_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    blocking_notes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
