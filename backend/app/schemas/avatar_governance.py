from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AvatarPolicyStateView(BaseModel):
    avatar_id: UUID
    state: str
    priority_weight: float
    exploration_weight: float
    risk_weight: float
    continuity_confidence: float | None = None
    quality_confidence: float | None = None
    cooldown_until: datetime | None = None
    notes: dict[str, Any] = Field(default_factory=dict)


class AvatarPromotionDecision(BaseModel):
    avatar_id: UUID
    action: str
    reason_code: str
    previous_state: str | None = None
    new_state: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class AvatarOutcomePayload(BaseModel):
    avatar_id: UUID
    project_id: UUID | None = None
    workspace_id: UUID | None = None
    tournament_run_id: UUID | None = None
    actual_ctr: float | None = None
    actual_retention: float | None = None
    actual_watch_time: float | None = None
    actual_conversion: float | None = None
    actual_publish_score: float | None = None
    continuity_health: float | None = None
    brand_drift_score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
