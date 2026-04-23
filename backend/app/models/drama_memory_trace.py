"""drama_memory_trace — narrative memory/wound record for a drama character."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DramaMemoryTrace(Base):
    """A remembered event that shapes how a character behaves in future scenes.

    Distinct from ``AvatarMemoryTrace`` (which is avatar-centric); this model
    is part of the Multi-Character Drama system and can link two characters.
    """

    __tablename__ = "drama_memory_trace"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    character_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    related_character_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    project_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    source_scene_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    event_type: Mapped[str] = mapped_column(String(64), nullable=False, default="interaction")
    emotional_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)

    # Relationship impact
    trust_impact: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    shame_impact: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fear_impact: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    dominance_impact: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    meaning_label: Mapped[str | None] = mapped_column(String(256), nullable=True)
    narrative_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    decay_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.05)
    persistence_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    recall_trigger: Mapped[str | None] = mapped_column(String(256), nullable=True)

    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
