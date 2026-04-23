"""drama_arc_progress — tracks a character's arc stage across an episode/series."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DramaArcProgress(Base):
    """Tracks arc progression for a character within an episode or series.

    Updated by ArcEngine after every scene outcome is resolved.
    """

    __tablename__ = "drama_arc_progress"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    character_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    project_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    episode_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    arc_name: Mapped[str] = mapped_column(String(128), nullable=False, default="main")
    arc_stage: Mapped[str] = mapped_column(String(64), nullable=False, default="ordinary_world")

    false_belief: Mapped[str | None] = mapped_column(Text, nullable=True)
    pressure_index: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    transformation_index: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    collapse_risk: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    mask_break_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    truth_acceptance_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    relation_entanglement_index: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    arc_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, onupdate=_now, index=True
    )
