"""policy_adapter — adapts per-avatar policy weights and dynamic thresholds from feedback."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.avatar_learning_state import AvatarLearningState
from app.schemas.avatar_learning import BaselineSnapshot, PolicyState

_WEIGHT_STEP = 0.05
_WEIGHT_MIN = 0.0
_WEIGHT_MAX = 1.0


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PolicyAdapter:
    """Adjusts per-avatar adaptive weights and dynamic thresholds based on the
    latest feedback metrics and their relationship to the context baseline.

    Called once per feedback cycle from :class:`AdaptiveLearningEngine`.
    """

    def adapt(
        self,
        db: Session,
        *,
        avatar_id: str,
        baseline: BaselineSnapshot,
        recent_metrics: dict[str, Any],
    ) -> PolicyState:
        """Update policy weights for *avatar_id* and return the new state.

        - If recent retention > baseline retention -> increase priority_weight.
        - Otherwise -> increase risk_weight.
        - Dynamic thresholds are set to 70% of the current baseline EWMA.
        """
        state = self._get_or_create(db, avatar_id=avatar_id)

        recent_retention = float(
            recent_metrics.get("retention") or recent_metrics.get("retention_30s") or 0.0
        )

        if baseline.retention_ewma > 0 and recent_retention > baseline.retention_ewma:
            state.priority_weight = min(_WEIGHT_MAX, state.priority_weight + _WEIGHT_STEP)
            state.positive_outcomes += 1
        else:
            state.risk_weight = min(_WEIGHT_MAX, state.risk_weight + _WEIGHT_STEP)

        # Dynamic thresholds: 70% of the running EWMA (floored at absolute minimums)
        state.dynamic_retention_threshold = max(0.20, baseline.retention_ewma * 0.70)
        state.dynamic_ctr_threshold = max(0.02, baseline.ctr_ewma * 0.70)

        # Clamp weights
        state.priority_weight = max(_WEIGHT_MIN, min(_WEIGHT_MAX, state.priority_weight))
        state.risk_weight = max(_WEIGHT_MIN, min(_WEIGHT_MAX, state.risk_weight))
        state.total_outcomes += 1
        state.updated_at = _now()

        db.commit()
        return self._to_state(state)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_or_create(self, db: Session, *, avatar_id: str) -> AvatarLearningState:
        row = (
            db.query(AvatarLearningState)
            .filter(AvatarLearningState.avatar_id == avatar_id)
            .one_or_none()
        )
        if row is None:
            row = AvatarLearningState(avatar_id=avatar_id)
            db.add(row)
            db.commit()
        return row

    @staticmethod
    def _to_state(row: AvatarLearningState) -> PolicyState:
        return PolicyState(
            avatar_id=row.avatar_id,
            priority_weight=row.priority_weight,
            exploration_weight=row.exploration_weight,
            risk_weight=row.risk_weight,
            dynamic_retention_threshold=row.dynamic_retention_threshold,
            dynamic_ctr_threshold=row.dynamic_ctr_threshold,
        )
