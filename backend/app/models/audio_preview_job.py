from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AudioPreviewJob(Base):
    __tablename__ = "audio_preview_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    voice_profile_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    style_preset: Mapped[str] = mapped_column(String(64), nullable=False, default="natural_conversational")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    preview_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
