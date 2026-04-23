"""self_healing_engine — orchestrates anomaly detection → healing action for avatars."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.avatar_healing import AvatarHealingResult
from app.services.avatar.anomaly_detector import AvatarAnomalyDetector
from app.services.avatar.healing_action_executor import HealingActionExecutor

logger = logging.getLogger(__name__)


class SelfHealingEngine:
    """Detects performance anomalies from feedback metrics and applies the
    appropriate corrective action (rollback, switch, cooldown).

    Typical usage::

        result = SelfHealingEngine().process_feedback(
            db=db,
            avatar_id=avatar_id,
            metrics=metrics,
            context=context,
        )
        feedback_result["self_healing"] = result.model_dump()
    """

    def __init__(self) -> None:
        self._detector = AvatarAnomalyDetector()
        self._executor = HealingActionExecutor()

    # ── Public API ────────────────────────────────────────────────────────────

    def process_feedback(
        self,
        db: Session,
        *,
        avatar_id: str,
        metrics: dict[str, Any],
        context: dict[str, Any] | None = None,
        baseline: dict[str, Any] | None = None,
    ) -> AvatarHealingResult:
        """Evaluate metrics and apply a healing action if an anomaly is found.

        Parameters
        ----------
        db:
            Active database session.
        avatar_id:
            The avatar under evaluation.
        metrics:
            Post-publish metrics dict.
        context:
            Optional extra context used by the action executor (e.g.
            ``candidate_avatar_ids``, ``current_state``).
        baseline:
            Optional EWMA baseline for relative anomaly detection.

        Returns
        -------
        :class:`AvatarHealingResult`
        """
        context = context or {}
        context.setdefault("avatar_id", avatar_id)
        context["metrics"] = metrics

        anomaly_report = self._detector.detect(metrics, baseline=baseline)

        if not anomaly_report.has_anomaly:
            return AvatarHealingResult(
                status="healthy",
                avatar_id=avatar_id,
            )

        action = self._decide_action(anomaly_report.anomaly_type, metrics)
        result_payload = self._execute(db, action=action, avatar_id=avatar_id, context=context)

        self._persist_event(
            db,
            avatar_id=avatar_id,
            anomaly=anomaly_report.anomaly_type,
            action=action,
            metrics=metrics,
            result_payload=result_payload,
            context=context,
        )

        return AvatarHealingResult(
            status="healed",
            anomaly=anomaly_report.anomaly_type,
            action=action,
            result=result_payload,
            avatar_id=avatar_id,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _decide_action(anomaly_type: str | None, metrics: dict[str, Any]) -> str:
        if anomaly_type == "retention_drop":
            return "rollback_avatar"
        if anomaly_type == "ctr_drop":
            return "switch_avatar"
        if anomaly_type == "continuity_break":
            return "cooldown_avatar"
        return "none"

    def _execute(
        self,
        db: Session,
        *,
        action: str,
        avatar_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            if action == "rollback_avatar":
                return self._executor.rollback(db, avatar_id=avatar_id, context=context)
            if action == "switch_avatar":
                return self._executor.switch_avatar(db, context=context)
            if action == "cooldown_avatar":
                return self._executor.cooldown(db, avatar_id=avatar_id, context=context)
        except Exception as exc:
            logger.warning("SelfHealingEngine._execute failed for action=%s: %s", action, exc)
            return {"action": action, "error": str(exc)}
        return {}

    @staticmethod
    def _persist_event(
        db: Session,
        *,
        avatar_id: str,
        anomaly: str | None,
        action: str,
        metrics: dict[str, Any],
        result_payload: dict[str, Any],
        context: dict[str, Any],
    ) -> None:
        try:
            from app.models.avatar_healing_event import AvatarHealingEvent
            db.add(
                AvatarHealingEvent(
                    avatar_id=avatar_id,
                    anomaly=anomaly,
                    action=action,
                    project_id=context.get("project_id"),
                    source_metrics=metrics,
                    result_payload=result_payload,
                )
            )
            db.commit()
        except Exception as exc:
            logger.warning("Failed to persist AvatarHealingEvent: %s", exc)
