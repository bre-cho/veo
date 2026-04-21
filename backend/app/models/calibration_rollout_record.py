from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CalibrationRolloutRecord(Base):
    __tablename__ = "calibration_rollout_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    context_key: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    platform: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    product_category: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    canary_stage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_weights: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    rollback_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    rollback_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reverted_to_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    context: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    payload: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=_now, onupdate=_now)

