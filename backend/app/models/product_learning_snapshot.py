"""ProductLearningSnapshot — SQLAlchemy model for product/persona learning snapshots."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ProductLearningSnapshot(Base):
    """Persists a point-in-time snapshot of product+persona performance learning.

    Written when ``ProductPerformanceModel.take_snapshot()`` is called (guard:
    sample_count >= 3).  Used by downstream recommendation layers to quickly
    access top hook/CTA styles without re-aggregating the full record set.
    """

    __tablename__ = "product_learning_snapshots"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    product_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    persona_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    top_hook_style: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    top_cta_style: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    avg_conversion: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Full aggregated payload for richer downstream use
    aggregated_data: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    snapshotted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, onupdate=_now
    )
