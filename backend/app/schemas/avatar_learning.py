"""avatar_learning — schemas for adaptive learning engine results."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BaselineSnapshot(BaseModel):
    """A point-in-time snapshot of the EWMA baseline for a context."""

    topic_signature: str | None = None
    template_family: str | None = None
    platform: str | None = None
    ctr_ewma: float = 0.0
    retention_ewma: float = 0.0
    watch_time_ewma: float = 0.0
    conversion_ewma: float = 0.0
    sample_count: int = 0


class BanditArmState(BaseModel):
    """Current state of a Thompson-sampling arm."""

    avatar_id: str
    template_family: str
    pulls: int = 0
    alpha: float = 1.0
    beta: float = 1.0
    mean_reward: float = 0.5


class PolicyState(BaseModel):
    """Adaptive policy weights for an avatar."""

    avatar_id: str
    priority_weight: float = 0.5
    exploration_weight: float = 0.2
    risk_weight: float = 0.2
    dynamic_retention_threshold: float = 0.4
    dynamic_ctr_threshold: float = 0.06


class AdaptiveLearningResult(BaseModel):
    """Result returned by AdaptiveLearningEngine.learn()."""

    avatar_id: str
    reward: float
    baseline: BaselineSnapshot
    policy: PolicyState
    extra: dict[str, Any] = Field(default_factory=dict)
