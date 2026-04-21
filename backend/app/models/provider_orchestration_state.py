from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ProviderOrchestrationState(Base):
    __tablename__ = "provider_orchestration_states"

    batch_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    stage: Mapped[str] = mapped_column(String(64), nullable=False, default="init", index=True)
    platform_states: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    recovery_state: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    compliance_state: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    manual_retry_state: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=_now, onupdate=_now, index=True)

