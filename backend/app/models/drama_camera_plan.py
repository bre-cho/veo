"""drama_camera_plan — full camera drama plan for a scene."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DramaCameraPlan(Base):
    """Camera psychology plan for a scene, derived from power + subtext.

    Camera decisions are mapped from psychological state, not aesthetic choice.
    Index: (scene_id), (emotional_anchor_character_id).
    """

    __tablename__ = "drama_camera_plan"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    scene_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    project_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    episode_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    # Focus and axis
    character_focus_priority: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    emotional_anchor_character_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    dominant_visual_axis: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Lens psychology
    lens_psychology_mode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    framing_mode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    eye_line_strategy: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Timing
    reveal_timing: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pause_hold_strategy: Mapped[str | None] = mapped_column(String(128), nullable=True)
    movement_strategy: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Notes
    blocking_sync_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    continuity_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Full shot sequence
    shot_sequence: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
