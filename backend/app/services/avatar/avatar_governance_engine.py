"""avatar_governance_engine — evaluates post-publish outcomes and applies
governance decisions (promote, demote, cooldown, rollback).

This engine is called from BrainFeedbackService after each publish outcome.
It reads the avatar's current policy state, applies the governance rules,
and writes the resulting state transitions and audit events.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.avatar_policy_state import AvatarPolicyState
from app.models.avatar_promotion_event import AvatarPromotionEvent
from app.schemas.avatar_governance import AvatarPromotionDecision
from app.services.avatar.avatar_policy_engine import AvatarPolicyEngine
from app.services.avatar.avatar_rollback_service import AvatarRollbackService


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AvatarGovernanceEngine:
    """Evaluates avatar outcome data and applies governance state transitions."""

    def __init__(self) -> None:
        self._policy = AvatarPolicyEngine()
        self._rollback = AvatarRollbackService()

    # ── Public API ────────────────────────────────────────────────────────────

    def evaluate_avatar_outcome(
        self,
        db: Session,
        *,
        avatar_id: str,
        metrics: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AvatarPromotionDecision:
        """Evaluate post-publish metrics and apply the appropriate action.

        Parameters
        ----------
        avatar_id:
            The avatar whose outcome is being evaluated.
        metrics:
            Publish metrics dict (same shape as AvatarScorecard inputs +
            optional ``baseline_retention`` for delta comparison).
        context:
            Optional dict with ``project_id``, ``topic_class``, etc.
        """
        context = context or {}
        policy_state = self._get_or_create_policy_state(db, avatar_id=avatar_id)
        current_state = policy_state.state

        # Extract metric signals
        total_score = float(metrics.get("total_score", 0.0))
        retention = float(metrics.get("retention_30s", 0.0))
        baseline_retention = float(metrics.get("baseline_retention", retention))
        retention_drop = max(0.0, baseline_retention - retention)

        has_continuity_break = bool(context.get("continuity_break"))
        has_brand_drift = bool(context.get("brand_drift"))
        consecutive_losses = int(metrics.get("consecutive_losses", 0))
        outcome_count = int(metrics.get("outcome_count", 1))
        consecutive_wins = int(metrics.get("consecutive_wins", 0))

        # ── Decide action ─────────────────────────────────────────────────
        action: str
        reason_code: str

        # Blocked / retired → no changes
        if current_state in ("blocked", "retired"):
            return AvatarPromotionDecision(
                avatar_id=avatar_id,
                action="none",
                reason_code="state_locked",
                previous_state=current_state,
                new_state=current_state,
                evidence=metrics,
            )

        # Cooldown check
        if self._policy.is_in_cooldown(policy_state.cooldown_until):
            if total_score >= 0.50:
                self._rollback.reactivate(db, avatar_id=avatar_id, reason_code="recovery_signal")
                return AvatarPromotionDecision(
                    avatar_id=avatar_id,
                    action="reactivate",
                    reason_code="recovery_signal",
                    previous_state="cooldown",
                    new_state="active",
                    evidence=metrics,
                )
            return AvatarPromotionDecision(
                avatar_id=avatar_id,
                action="none",
                reason_code="in_cooldown",
                previous_state="cooldown",
                new_state="cooldown",
                evidence=metrics,
            )

        # Rollback check
        if self._policy.should_rollback(
            total_score=total_score, retention_drop=retention_drop
        ):
            new_state = self._rollback.rollback(
                db,
                avatar_id=avatar_id,
                from_state=current_state,
                reason_code="retention_drop" if retention_drop >= 0.15 else "low_score",
                source_metrics=metrics,
            )
            return AvatarPromotionDecision(
                avatar_id=avatar_id,
                action="rollback",
                reason_code="retention_drop" if retention_drop >= 0.15 else "low_score",
                previous_state=current_state,
                new_state=new_state,
                evidence=metrics,
            )

        # Cooldown check (continuity / brand drift / consecutive losses)
        if self._policy.should_cooldown(
            has_continuity_break=has_continuity_break,
            has_brand_drift=has_brand_drift,
            consecutive_losses=consecutive_losses,
        ):
            reason_code = (
                "continuity_break"
                if has_continuity_break
                else "brand_drift"
                if has_brand_drift
                else "consecutive_losses"
            )
            new_state = self._rollback.cooldown(
                db,
                avatar_id=avatar_id,
                from_state=current_state,
                reason_code=reason_code,
                source_metrics=metrics,
            )
            return AvatarPromotionDecision(
                avatar_id=avatar_id,
                action="cooldown",
                reason_code=reason_code,
                previous_state=current_state,
                new_state=new_state,
                evidence=metrics,
            )

        # Promotion checks
        if current_state == "candidate" and self._policy.should_promote_to_active(
            total_score=total_score, outcome_count=outcome_count
        ):
            new_state = self._promote(
                db,
                avatar_id=avatar_id,
                from_state="candidate",
                to_state="active",
                reason_code="threshold_reached",
                source_metrics=metrics,
            )
            return AvatarPromotionDecision(
                avatar_id=avatar_id,
                action="promote",
                reason_code="threshold_reached",
                previous_state="candidate",
                new_state=new_state,
                evidence=metrics,
            )

        if current_state == "active" and self._policy.should_promote_to_priority(
            total_score=total_score,
            consecutive_wins=consecutive_wins,
        ):
            new_state = self._promote(
                db,
                avatar_id=avatar_id,
                from_state="active",
                to_state="priority",
                reason_code="priority_win_streak",
                source_metrics=metrics,
            )
            return AvatarPromotionDecision(
                avatar_id=avatar_id,
                action="promote",
                reason_code="priority_win_streak",
                previous_state="active",
                new_state=new_state,
                evidence=metrics,
            )

        return AvatarPromotionDecision(
            avatar_id=avatar_id,
            action="none",
            reason_code="stable",
            previous_state=current_state,
            new_state=current_state,
            evidence=metrics,
        )

    def get_policy_state(
        self, db: Session, *, avatar_id: str
    ) -> AvatarPolicyState | None:
        return (
            db.query(AvatarPolicyState)
            .filter(AvatarPolicyState.avatar_id == avatar_id)
            .first()
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_or_create_policy_state(
        self, db: Session, *, avatar_id: str
    ) -> AvatarPolicyState:
        row = self.get_policy_state(db, avatar_id=avatar_id)
        if row is None:
            row = AvatarPolicyState(
                avatar_id=avatar_id,
                state="candidate",
                priority_weight=0.5,
                exploration_weight=0.2,
                risk_weight=0.0,
            )
            db.add(row)
            db.commit()
        return row

    def _promote(
        self,
        db: Session,
        *,
        avatar_id: str,
        from_state: str,
        to_state: str,
        reason_code: str,
        source_metrics: dict[str, Any],
    ) -> str:
        row = self.get_policy_state(db, avatar_id=avatar_id)
        if row is None:
            return from_state
        row.state = to_state
        row.last_promotion_at = _now()
        if to_state == "priority":
            row.priority_weight = min(row.priority_weight + 0.1, 1.0)
        db.commit()
        db.add(
            AvatarPromotionEvent(
                avatar_id=avatar_id,
                event_type="promote",
                from_state=from_state,
                to_state=to_state,
                reason_code=reason_code,
                source_metric_json=source_metrics,
            )
        )
        db.commit()
        return to_state
