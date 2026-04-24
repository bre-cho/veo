from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class DramaMemoryTrace(Base):
    __tablename__ = "drama_memory_traces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    episode_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drama_character_profiles.id"), nullable=False, index=True)
    related_character_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("drama_character_profiles.id"), nullable=True, index=True)
    source_scene_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    meaning_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    recall_trigger: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    emotional_weight: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    trust_impact: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    shame_impact: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    fear_impact: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    dominance_impact: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    persistence_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    decay_rate: Mapped[float] = mapped_column(Float, default=0.05, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
