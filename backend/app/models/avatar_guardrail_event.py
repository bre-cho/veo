"""avatar_guardrail_event — records when an avatar triggers a guardrail."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AvatarGuardrailEvent(Base):
    """One row per guardrail violation.

    Written when a continuity break, brand drift, retention drop or
    other policy violation is detected for an avatar.
    """

    __tablename__ = "avatar_guardrail_event"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    avatar_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    guardrail_code: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # continuity_break|brand_drift|retention_drop|policy_violation
    severity: Mapped[str] = mapped_column(
        String(16), nullable=False, default="warning"
    )  # info|warning|critical
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    action_taken: Mapped[str] = mapped_column(
        String(32), nullable=False, default="none"
    )  # none|downweight|cooldown|rollback|block
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
