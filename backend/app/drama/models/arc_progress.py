from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DramaArcProgress(Base):
    __tablename__ = "drama_arc_progress"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    episode_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drama_character_profiles.id"), nullable=False, index=True)

    arc_name: Mapped[str] = mapped_column(String(128), nullable=False)
    arc_stage: Mapped[str] = mapped_column(String(64), default="mask_stable", nullable=False, index=True)
    false_belief: Mapped[str | None] = mapped_column(Text, nullable=True)

    pressure_index: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    transformation_index: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    collapse_risk: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    mask_break_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    truth_acceptance_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    relation_entanglement_index: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    latest_scene_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
