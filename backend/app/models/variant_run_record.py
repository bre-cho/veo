from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class VariantRunRecord(Base):
    """DB-backed record for a review-variant generation run.

    Persists the variants generated, the winner selected, and — once a publish
    signal arrives — the actual conversion outcome.  This replaces the
    in-memory ``_VARIANT_HISTORY`` list so data survives restarts.
    """

    __tablename__ = "variant_run_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    product_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    product_category: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    platform: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    market_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    winner_variant_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    winner_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    winner_score_breakdown: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    variants: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    context: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    # Outcome columns — populated when a publish signal arrives
    actual_conversion_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_view_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_ctr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    outcome_recorded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, onupdate=_now
    )
