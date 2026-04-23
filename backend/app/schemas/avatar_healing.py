"""avatar_healing — schemas for self-healing engine results."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AvatarHealingResult(BaseModel):
    """Result returned by SelfHealingEngine.process_feedback()."""

    status: str  # healthy | healed | failed
    anomaly: str | None = None  # None when status=healthy
    action: str = "none"  # rollback_avatar | switch_avatar | cooldown_avatar | none
    result: dict[str, Any] = Field(default_factory=dict)
    avatar_id: str | None = None


class AvatarAnomalyReport(BaseModel):
    """Structured anomaly report from AvatarAnomalyDetector."""

    has_anomaly: bool = False
    anomaly_type: str | None = None  # retention_drop | ctr_drop | continuity_break
    severity: str = "none"  # none | low | medium | high | critical
    retention: float | None = None
    ctr: float | None = None
    continuity_health: float | None = None
    baseline_retention: float | None = None
    baseline_ctr: float | None = None
