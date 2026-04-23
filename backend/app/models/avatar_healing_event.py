"""avatar_healing_event — audit log for self-healing actions applied to avatars."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AvatarHealingEvent(Base):
    """Immutable audit record written whenever the self-healing engine takes
    an action on an avatar (rollback, switch, cooldown, none).
    """

    __tablename__ = "avatar_healing_event"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    avatar_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    anomaly: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # retention_crash|ctr_drop|continuity_break|none
    action: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # rollback_avatar|switch_avatar|cooldown_avatar|none
    project_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source_metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    result_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
