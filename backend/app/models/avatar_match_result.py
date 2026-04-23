from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

try:
    from app.db.base_class import Base
except Exception:  # pragma: no cover
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):
        pass


class AvatarMatchResult(Base):
    __tablename__ = "avatar_match_result"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tournament_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("avatar_tournament_run.id", ondelete="CASCADE"), nullable=False, index=True
    )
    avatar_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    topic_signature: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    platform: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    predicted_score: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    predicted_ctr: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    predicted_retention: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    predicted_conversion: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    continuity_score: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    brand_fit_score: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    pair_fit_score: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    governance_penalty: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    final_rank_score: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False, default=0)

    actual_ctr: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    actual_retention: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    actual_watch_time: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    actual_conversion: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    actual_publish_score: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    fitness_score: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)

    result_label: Mapped[str] = mapped_column(String(32), nullable=False, default="neutral", index=True)
    selection_rank: Mapped[int] = mapped_column(nullable=False, default=0)
    was_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    was_exploration: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
