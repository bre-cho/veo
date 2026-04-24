from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DramaPowerShift(Base):
    __tablename__ = "drama_power_shifts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    episode_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    scene_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    from_character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drama_character_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    to_character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drama_character_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    trigger_event: Mapped[str | None] = mapped_column(String(64), nullable=True)

    social_delta: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    emotional_delta: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    informational_delta: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    moral_delta: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    spatial_delta: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    narrative_control_delta: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
