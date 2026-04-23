from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.avatar_guardrail_event import AvatarGuardrailEvent
from app.models.avatar_policy_state import AvatarPolicyState
from app.models.avatar_promotion_event import AvatarPromotionEvent
from app.schemas.avatar_governance import AvatarOutcomePayload, AvatarPromotionDecision
from app.services.avatar.avatar_policy_engine import AvatarPolicyEngine
from app.services.avatar.avatar_rollback_service import AvatarRollbackService


class AvatarGovernanceEngine:
    def __init__(self, db: Session, policy_engine: AvatarPolicyEngine | None = None, rollback_service: AvatarRollbackService | None = None) -> None:
        self.db = db
        self.policy_engine = policy_engine or AvatarPolicyEngine()
        self.rollback_service = rollback_service or AvatarRollbackService()

    def evaluate_avatar_outcome(self, payload: AvatarOutcomePayload) -> AvatarPromotionDecision:
        state = self._get_or_create_state(payload.avatar_id)
        previous_state = state.state

        if payload.brand_drift_score is not None and payload.brand_drift_score > 0.70:
            self._emit_guardrail(payload, code="brand_drift", severity="warning", action_taken="downweight")
            state.risk_weight = float(state.risk_weight) + 0.25

        if self.rollback_service.should_rollback(
            actual_publish_score=payload.actual_publish_score,
            actual_retention=payload.actual_retention,
            baseline_retention=float(state.quality_confidence) if state.quality_confidence is not None else None,
        ):
            state.state = "cooldown"
            state.cooldown_until = self.policy_engine.compute_cooldown_until()
            state.last_rollback_at = datetime.now(timezone.utc)
            action = "rollback"
            reason_code = "retention_or_publish_crash"
        elif payload.actual_publish_score is not None and payload.actual_publish_score >= 0.75:
            state.state = "priority"
            state.priority_weight = max(float(state.priority_weight), 1.25)
            state.last_promotion_at = datetime.now(timezone.utc)
            action = "promote"
            reason_code = "strong_publish_score"
        elif payload.actual_publish_score is not None and payload.actual_publish_score >= 0.55:
            state.state = "active"
            state.priority_weight = max(float(state.priority_weight), 1.0)
            action = "stabilize"
            reason_code = "acceptable_publish_score"
        else:
            state.state = "candidate"
            action = "demote"
            reason_code = "insufficient_signal"

        if payload.continuity_health is not None:
            state.continuity_confidence = payload.continuity_health
        if payload.actual_retention is not None:
            state.quality_confidence = payload.actual_retention

        event = AvatarPromotionEvent(
            avatar_id=payload.avatar_id,
            event_type=action,
            from_state=previous_state,
            to_state=state.state,
            reason_code=reason_code,
            reason_text=f"Avatar governance action={action}",
            source_metric_json=json.dumps(payload.model_dump(mode="json")),
        )
        self.db.add(state)
        self.db.add(event)
        self.db.commit()
        self.db.refresh(state)

        return AvatarPromotionDecision(
            avatar_id=payload.avatar_id,
            action=action,
            reason_code=reason_code,
            previous_state=previous_state,
            new_state=state.state,
            evidence=payload.model_dump(mode="json"),
        )

    def _get_or_create_state(self, avatar_id):
        state = self.db.query(AvatarPolicyState).filter(AvatarPolicyState.avatar_id == avatar_id).one_or_none()
        if state:
            return state
        state = AvatarPolicyState(avatar_id=avatar_id)
        self.db.add(state)
        self.db.flush()
        return state

    def _emit_guardrail(self, payload: AvatarOutcomePayload, *, code: str, severity: str, action_taken: str) -> None:
        self.db.add(
            AvatarGuardrailEvent(
                avatar_id=payload.avatar_id,
                project_id=payload.project_id,
                guardrail_code=code,
                severity=severity,
                payload_json=json.dumps(payload.model_dump(mode="json")),
                action_taken=action_taken,
            )
        )
