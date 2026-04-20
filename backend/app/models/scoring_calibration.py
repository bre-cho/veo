from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ScoringCalibration(Base):
    """Persists calibrated scoring weights for ConversionScoringEngine.

    When ≥30 performance records are available for a platform+category
    combination, ``calibrate_weights()`` computes optimal weights via
    linear regression and stores them here.  The engine loads them at
    score time to replace static heuristic weights.
    """

    __tablename__ = "scoring_calibrations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    platform: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    product_category: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    # JSON dict of dimension → weight  (e.g. {"hook_strength": 0.18, ...})
    weights: Mapped[Any] = mapped_column(JSON, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    r_squared: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    calibrated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, onupdate=_now
    )
