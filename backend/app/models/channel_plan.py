from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ChannelPlan(Base):
    __tablename__ = "channel_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    avatar_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    product_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    channel_name: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    niche: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    market_code: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    goal: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    request_context: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    selected_variants: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    ranking_scores: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    final_plan: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parent_plan_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    payload: Mapped[Any] = mapped_column(JSON, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
        index=True,
    )
