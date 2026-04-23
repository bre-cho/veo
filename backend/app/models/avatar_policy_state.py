from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

try:
    from app.db.base_class import Base
except Exception:  # pragma: no cover
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):
        pass


class AvatarPolicyState(Base):
    __tablename__ = "avatar_policy_state"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    avatar_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="candidate", index=True)
    priority_weight: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False, default=1.0)
    exploration_weight: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False, default=0.15)
    risk_weight: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False, default=0.0)
    continuity_confidence: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    quality_confidence: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_promotion_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_demotion_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_rollback_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
