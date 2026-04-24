from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class DramaSceneState(Base):
    __tablename__ = "drama_scene_states"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    episode_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    scene_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True, index=True)

    scene_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    visible_conflict: Mapped[str | None] = mapped_column(Text, nullable=True)
    hidden_conflict: Mapped[str | None] = mapped_column(Text, nullable=True)
    scene_temperature: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    pressure_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    dominant_character_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    emotional_center_character_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    threatened_character_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    turning_point: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    power_shift_delta: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    trust_shift_delta: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    exposure_shift_delta: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    dependency_shift_delta: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    analysis_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    continuity_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    compile_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
