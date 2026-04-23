"""avatar_rollback_service — handles avatar rollback and state recovery.

When an avatar that is currently active or priority causes a meaningful drop
in key metrics, this service decides how to respond:

  1. ``rollback``     — switch back to the most-recently stable avatar
  2. ``downweight``   — reduce priority_weight significantly
  3. ``cooldown``     — block from exploitation for N publish cycles

The caller (AvatarGovernanceEngine) drives the decision; this service
executes the DB updates and writes the audit trail.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.avatar_guardrail_event import AvatarGuardrailEvent
from app.models.avatar_policy_state import AvatarPolicyState
from app.models.avatar_promotion_event import AvatarPromotionEvent


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AvatarRollbackService:
    """Executes avatar rollback, downweight, or cooldown operations."""

    # ── Core actions ──────────────────────────────────────────────────────────

    def rollback(
        self,
        db: Session,
        *,
        avatar_id: str,
        from_state: str,
        reason_code: str = "retention_drop",
        reason_text: str | None = None,
        source_metrics: dict[str, Any] | None = None,
    ) -> str:
        """Put avatar into cooldown and write audit trail. Returns new state."""
        new_state = "cooldown"
        cooldown_until = _now() + timedelta(days=5)
        self._upsert_policy_state(
            db,
            avatar_id=avatar_id,
            state=new_state,
            cooldown_until=cooldown_until,
            risk_weight=0.5,
        )
        self._write_promotion_event(
            db,
            avatar_id=avatar_id,
            event_type="rollback",
            from_state=from_state,
            to_state=new_state,
            reason_code=reason_code,
            reason_text=reason_text,
            source_metrics=source_metrics or {},
        )
        self._write_guardrail_event(
            db,
            avatar_id=avatar_id,
            guardrail_code=reason_code,
            severity="warning",
            payload=source_metrics or {},
            action_taken="rollback",
        )
        return new_state

    def downweight(
        self,
        db: Session,
        *,
        avatar_id: str,
        current_priority_weight: float,
        factor: float = 0.5,
        reason_code: str = "performance_decay",
        source_metrics: dict[str, Any] | None = None,
    ) -> float:
        """Halve the priority weight and write a demotion event."""
        new_weight = round(current_priority_weight * factor, 4)
        self._upsert_policy_state(db, avatar_id=avatar_id, priority_weight=new_weight)
        self._write_promotion_event(
            db,
            avatar_id=avatar_id,
            event_type="demote",
            from_state="active",
            to_state="active",
            reason_code=reason_code,
            source_metrics=source_metrics or {},
        )
        return new_weight

    def cooldown(
        self,
        db: Session,
        *,
        avatar_id: str,
        from_state: str,
        days: int = 5,
        reason_code: str = "continuity_break",
        reason_text: str | None = None,
        source_metrics: dict[str, Any] | None = None,
    ) -> str:
        """Put avatar into cooldown for `days` publish cycles."""
        new_state = "cooldown"
        cooldown_until = _now() + timedelta(days=days)
        self._upsert_policy_state(
            db,
            avatar_id=avatar_id,
            state=new_state,
            cooldown_until=cooldown_until,
        )
        self._write_promotion_event(
            db,
            avatar_id=avatar_id,
            event_type="cooldown",
            from_state=from_state,
            to_state=new_state,
            reason_code=reason_code,
            reason_text=reason_text,
            source_metrics=source_metrics or {},
        )
        self._write_guardrail_event(
            db,
            avatar_id=avatar_id,
            guardrail_code=reason_code,
            severity="warning",
            payload=source_metrics or {},
            action_taken="cooldown",
        )
        return new_state

    def reactivate(
        self,
        db: Session,
        *,
        avatar_id: str,
        reason_code: str = "cooldown_expired",
    ) -> str:
        """Reactivate a cooldown/blocked avatar back to active."""
        new_state = "active"
        self._upsert_policy_state(
            db,
            avatar_id=avatar_id,
            state=new_state,
            cooldown_until=None,
            risk_weight=0.0,
        )
        self._write_promotion_event(
            db,
            avatar_id=avatar_id,
            event_type="reactivate",
            from_state="cooldown",
            to_state=new_state,
            reason_code=reason_code,
        )
        return new_state

    # ── DB helpers ────────────────────────────────────────────────────────────

    def _upsert_policy_state(
        self,
        db: Session,
        *,
        avatar_id: str,
        state: str | None = None,
        priority_weight: float | None = None,
        cooldown_until: datetime | None = None,
        risk_weight: float | None = None,
    ) -> None:
        row = (
            db.query(AvatarPolicyState)
            .filter(AvatarPolicyState.avatar_id == avatar_id)
            .first()
        )
        if row is None:
            row = AvatarPolicyState(avatar_id=avatar_id)
            db.add(row)
        if state is not None:
            row.state = state
            if state == "cooldown":
                row.last_rollback_at = _now()
            elif state == "active":
                row.last_promotion_at = _now()
        if priority_weight is not None:
            row.priority_weight = priority_weight
        if cooldown_until is not None:
            row.cooldown_until = cooldown_until
        elif state == "active":
            row.cooldown_until = None
        if risk_weight is not None:
            row.risk_weight = risk_weight
        db.commit()

    def _write_promotion_event(
        self,
        db: Session,
        *,
        avatar_id: str,
        event_type: str,
        from_state: str,
        to_state: str,
        reason_code: str,
        reason_text: str | None = None,
        source_metrics: dict[str, Any] | None = None,
    ) -> None:
        db.add(
            AvatarPromotionEvent(
                avatar_id=avatar_id,
                event_type=event_type,
                from_state=from_state,
                to_state=to_state,
                reason_code=reason_code,
                reason_text=reason_text,
                source_metric_json=source_metrics or {},
            )
        )
        db.commit()

    def _write_guardrail_event(
        self,
        db: Session,
        *,
        avatar_id: str,
        guardrail_code: str,
        severity: str,
        payload: dict[str, Any],
        action_taken: str,
        project_id: str | None = None,
    ) -> None:
        db.add(
            AvatarGuardrailEvent(
                avatar_id=avatar_id,
                project_id=project_id,
                guardrail_code=guardrail_code,
                severity=severity,
                payload_json=payload,
                action_taken=action_taken,
            )
        )
        db.commit()
