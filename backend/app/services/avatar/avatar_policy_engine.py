from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(slots=True)
class GovernanceThresholds:
    promote_to_active_min_samples: int = 2
    promote_to_priority_min_samples: int = 3
    retention_drop_threshold: float = 0.12
    rollback_publish_score_threshold: float = 0.40
    cooldown_days: int = 7
    exploration_floor: float = 0.10


class AvatarPolicyEngine:
    def __init__(self, thresholds: GovernanceThresholds | None = None) -> None:
        self.thresholds = thresholds or GovernanceThresholds()

    def compute_cooldown_until(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(days=self.thresholds.cooldown_days)

    def get_exploration_floor(self) -> float:
        return self.thresholds.exploration_floor
