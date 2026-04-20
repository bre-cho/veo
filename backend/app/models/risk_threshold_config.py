"""RiskThresholdConfig — SQLAlchemy model for per-platform risk thresholds."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, Float, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RiskThresholdConfig(Base):
    """Per-platform, per-customer-tier risk threshold configuration.

    Overrides the default thresholds in ``ComplianceRiskPolicy`` when a row
    exists for the given platform + customer_tier combination.
    """

    __tablename__ = "risk_threshold_configs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    platform: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    customer_tier: Mapped[str] = mapped_column(
        String(64), nullable=False, default="standard", index=True
    )
    max_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.70)
    # JSON list of category strings that are always blocked for this tier
    blocked_categories: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, onupdate=_now
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now
    )
