"""avatar_governance — schemas for avatar policy state and promotion decisions."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class AvatarPolicyStateView(BaseModel):
    """Read-only view of an avatar's current governance policy state."""

    avatar_id: str
    state: str  # candidate|active|priority|cooldown|blocked|retired
    priority_weight: float = 0.5
    exploration_weight: float = 0.2
    risk_weight: float = 0.0
    continuity_confidence: float | None = None
    quality_confidence: float | None = None
    cooldown_until: datetime | None = None
    notes_text: str | None = None


class AvatarPromotionDecision(BaseModel):
    """Result of a governance promotion/demotion evaluation."""

    avatar_id: str
    action: str  # promote|demote|rollback|cooldown|reactivate|none
    reason_code: str
    previous_state: str
    new_state: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class AvatarGovernanceOutcomeRequest(BaseModel):
    """Input for evaluating post-publish outcome against governance rules."""

    avatar_id: str
    market_code: str | None = None
    content_goal: str | None = None
    topic_class: str | None = None
    project_id: str | None = None
    template_id: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    continuity_health: float | None = None  # 0.0–1.0
    brand_drift_score: float | None = None  # 0.0–1.0, higher = more drift


class AvatarRollbackRequest(BaseModel):
    """Request to force-rollback or change an avatar's governance state."""

    avatar_id: str
    action: str  # rollback|cooldown|reactivate|block
    reason_code: str = "manual_override"
    reason_text: str | None = None
