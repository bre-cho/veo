"""avatar_policy_state — current governance policy state for each avatar."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AvatarPolicyState(Base):
    """One row per avatar, updated as governance decisions are applied.

    Tracks the avatar's current lifecycle state and the weight parameters
    used during tournament scoring.

    State machine:
        candidate → active → priority → cooldown → blocked → retired
    """

    __tablename__ = "avatar_policy_state"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    avatar_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, default="candidate", index=True
    )  # candidate|active|priority|cooldown|blocked|retired

    priority_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    exploration_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    risk_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    continuity_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    last_promotion_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    last_demotion_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    last_rollback_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    cooldown_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    notes_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, onupdate=_now
    )
