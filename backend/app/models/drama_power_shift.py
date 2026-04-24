"""drama_power_shift — multi-dimensional power shift record per scene."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DramaPowerShift(Base):
    """Records a multi-dimensional power shift between two characters after a scene.

    Each dimension tracks a separate power axis: social, emotional,
    informational, moral, spatial, and narrative control.
    Index: (scene_id), (from_character_id, to_character_id).
    """

    __tablename__ = "drama_power_shift"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    scene_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    project_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    episode_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    from_character_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    to_character_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)

    # Multi-dimensional power deltas (negative = loss, positive = gain)
    social_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    emotional_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    informational_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    moral_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    spatial_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    narrative_control_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    trigger_event: Mapped[str | None] = mapped_column(String(128), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
