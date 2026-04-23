"""avatar_memory_trace — SQLAlchemy model for avatar narrative memory records."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AvatarMemoryTrace(Base):
    """A single episodic memory trace for an avatar.

    Stores emotionally weighted narrative events that the AvatarMemoryEngine
    uses to surface relevant past experiences when a scene trigger fires.
    """

    __tablename__ = "avatar_memory_trace"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    avatar_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    memory_type: Mapped[str] = mapped_column(String(64), nullable=False, default="event")
    trigger: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    emotional_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    narrative_summary: Mapped[str] = mapped_column(Text, nullable=False)
    continuity_tag: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source_scene_index: Mapped[int | None] = mapped_column(nullable=True)
    source_series_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
