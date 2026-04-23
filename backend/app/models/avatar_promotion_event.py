"""avatar_promotion_event — audit log for avatar state transitions."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AvatarPromotionEvent(Base):
    """Immutable audit record for every avatar state transition.

    Written when governance promotes, demotes, rolls back, puts into
    cooldown, or reactivates an avatar.
    """

    __tablename__ = "avatar_promotion_event"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    avatar_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # promote|demote|rollback|cooldown|reactivate
    from_state: Mapped[str] = mapped_column(String(32), nullable=False)
    to_state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_metric_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
