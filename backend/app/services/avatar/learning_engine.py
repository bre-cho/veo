"""learning_engine — adaptive learning orchestrator for avatar performance."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.avatar_learning import AdaptiveLearningResult
from app.services.avatar.bandit_engine import BanditEngine
from app.services.avatar.baseline_engine import BaselineEngine
from app.services.avatar.policy_adapter import PolicyAdapter

logger = logging.getLogger(__name__)


class AdaptiveLearningEngine:
    """Orchestrates the adaptive learning loop for avatars.

    On each feedback cycle it:
    1. Updates the EWMA context baseline.
    2. Computes a normalised reward signal.
    3. Updates the Thompson-sampling bandit arm.
    4. Adapts per-avatar policy weights and dynamic thresholds.

    Typical usage::

        result = AdaptiveLearningEngine().learn(
            db=db,
            avatar_id=avatar_id,
            context=context,
            metrics=metrics,
        )
        feedback_result["adaptive_learning"] = result.model_dump()
    """

    def __init__(self) -> None:
        self._baseline = BaselineEngine()
        self._bandit = BanditEngine()
        self._policy = PolicyAdapter()

    def learn(
        self,
        db: Session,
        *,
        avatar_id: str,
        context: dict[str, Any],
        metrics: dict[str, Any],
    ) -> AdaptiveLearningResult:
        """Run one learning cycle and return :class:`AdaptiveLearningResult`.

        Parameters
        ----------
        db:
            Active database session.
        avatar_id:
            The avatar whose performance is being learned from.
        context:
            Context dict with keys such as ``topic_signature``,
            ``template_family``, and ``platform``.
        metrics:
            Post-publish metric dict.
        """
        template_family = context.get("template_family") or "default"

        baseline = self._baseline.update(db, context=context, metrics=metrics)
        reward = self._compute_reward(metrics, baseline)
        bandit_state = self._bandit.update(
            db,
            avatar_id=avatar_id,
            template_family=template_family,
            reward=reward,
        )
        policy_state = self._policy.adapt(
            db,
            avatar_id=avatar_id,
            baseline=baseline,
            recent_metrics=metrics,
        )

        return AdaptiveLearningResult(
            avatar_id=avatar_id,
            reward=reward,
            baseline=baseline,
            policy=policy_state,
            extra={
                "bandit": bandit_state.model_dump(),
                "template_family": template_family,
            },
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _compute_reward(
        metrics: dict[str, Any],
        baseline: "BaselineSnapshot",  # noqa: F821
    ) -> float:
        """Normalise metrics against the running baseline to produce a reward
        signal in [0, 1].

        Weights: ctr 30%, retention 50%, conversion 20%.
        """
        from app.schemas.avatar_learning import BaselineSnapshot  # avoid circular at module level

        ctr = float(metrics.get("ctr") or 0.0)
        retention = float(
            metrics.get("retention") or metrics.get("retention_30s") or 0.0
        )
        conversion = float(metrics.get("conversion") or 0.0)

        def ratio(value: float, base: float) -> float:
            if base <= 0:
                return min(1.0, value)
            return min(1.0, value / base)

        r = (
            ratio(ctr, baseline.ctr_ewma) * 0.30
            + ratio(retention, baseline.retention_ewma) * 0.50
            + ratio(conversion, baseline.conversion_ewma) * 0.20
        )
        return max(0.0, min(1.0, r))
