"""avatar_bandit_state — Thompson-sampling arm state for avatar × template_family pairs."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AvatarBanditState(Base):
    """One row per (avatar_id, template_family) arm.

    Alpha/beta are the Beta-distribution parameters used for Thompson sampling.
    They are updated after each publish feedback cycle.
    """

    __tablename__ = "avatar_bandit_state"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    avatar_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    template_family: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    pulls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reward_sum: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Beta distribution parameters for Thompson sampling
    alpha: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    beta: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, onupdate=_now
    )

    __table_args__ = (
        UniqueConstraint(
            "avatar_id", "template_family", name="uq_avatar_bandit_state_avatar_id_template_family"
        ),
    )
