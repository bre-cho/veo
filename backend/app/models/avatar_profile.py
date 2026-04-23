"""avatar_profile — SQLAlchemy model for persisted avatar identity profiles."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AvatarProfile(Base):
    """Persistent record for a single avatar entity.

    Each row represents one named avatar (e.g. ``narrator_dark_doc_v1``) with
    its full identity profile, voice settings, and context affinity lists.
    """

    __tablename__ = "avatar_profile"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    avatar_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    persona: Mapped[str] = mapped_column(Text, nullable=False)
    narrative_role: Mapped[str] = mapped_column(String(64), nullable=False)
    tone: Mapped[str] = mapped_column(String(64), nullable=False)
    visual_style: Mapped[str] = mapped_column(String(128), nullable=False)
    belief_system: Mapped[str | None] = mapped_column(Text, nullable=True)
    market_code: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    # JSON lists / dicts stored as JSONB
    content_goals: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    topic_classes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    reference_image_urls: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    voice_profile: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
