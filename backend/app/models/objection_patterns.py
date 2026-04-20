from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ObjectionPattern(Base):
    """Stores objection phrases seeded from high-performing hooks.

    ``ExtendedReviewEngine`` queries this table by ``product_category`` +
    ``platform`` to surface real objections instead of hardcoded lists.
    """

    __tablename__ = "objection_patterns"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    objection_text: Mapped[str] = mapped_column(Text, nullable=False)
    product_category: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    platform: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    source_hook_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    avg_conversion_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, onupdate=_now
    )
