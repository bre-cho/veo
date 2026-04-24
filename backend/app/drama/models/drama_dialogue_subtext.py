from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DramaDialogueSubtext(Base):
    __tablename__ = "drama_dialogue_subtexts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    episode_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    scene_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    line_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    speaker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drama_character_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("drama_character_profiles.id", ondelete="SET NULL"), nullable=True, index=True)

    literal_intent: Mapped[str | None] = mapped_column(Text, nullable=True)
    hidden_intent: Mapped[str | None] = mapped_column(Text, nullable=True)
    psychological_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_subtext: Mapped[str | None] = mapped_column(Text, nullable=True)
    threat_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    honesty_level: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    mask_level: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
