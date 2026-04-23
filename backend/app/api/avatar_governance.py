"""avatar_governance — ops API for avatar governance state management."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.avatar_governance import (
    AvatarGovernanceOutcomeRequest,
    AvatarPolicyStateView,
    AvatarPromotionDecision,
    AvatarRollbackRequest,
)
from app.services.avatar.avatar_governance_engine import AvatarGovernanceEngine
from app.services.avatar.avatar_rollback_service import AvatarRollbackService

router = APIRouter(tags=["avatar-governance"])
_governance = AvatarGovernanceEngine()
_rollback = AvatarRollbackService()


# =========================
# Routes
# =========================

@router.get("/api/v1/avatar/governance/state/{avatar_id}", response_model=dict[str, Any])
async def get_governance_state(
    avatar_id: str,
    db: Session = Depends(get_db),
):
    """Get the current governance policy state for an avatar."""
    policy = _governance.get_policy_state(db, avatar_id=avatar_id)
    if policy is None:
        # Return default candidate state if no record exists
        return {
            "ok": True,
            "data": {
                "avatar_id": avatar_id,
                "state": "candidate",
                "priority_weight": 0.5,
                "exploration_weight": 0.2,
                "risk_weight": 0.0,
                "continuity_confidence": None,
                "quality_confidence": None,
                "cooldown_until": None,
                "notes_text": None,
            },
            "error": None,
        }

    view = AvatarPolicyStateView(
        avatar_id=policy.avatar_id,
        state=policy.state,
        priority_weight=policy.priority_weight,
        exploration_weight=policy.exploration_weight,
        risk_weight=policy.risk_weight,
        continuity_confidence=policy.continuity_confidence,
        quality_confidence=policy.quality_confidence,
        cooldown_until=policy.cooldown_until,
        notes_text=policy.notes_text,
    )
    return {"ok": True, "data": view.model_dump(), "error": None}


@router.post(
    "/api/v1/avatar/governance/recalculate/{avatar_id}",
    response_model=dict[str, Any],
)
async def recalculate_governance(
    avatar_id: str,
    payload: AvatarGovernanceOutcomeRequest,
    db: Session = Depends(get_db),
):
    """Re-evaluate governance state from the provided metrics."""
    try:
        decision = _governance.evaluate_avatar_outcome(
            db,
            avatar_id=avatar_id,
            metrics=payload.metrics,
            context={
                "project_id": payload.project_id,
                "topic_class": payload.topic_class,
                "continuity_break": payload.continuity_health is not None
                and payload.continuity_health < 0.3,
                "brand_drift": payload.brand_drift_score is not None
                and payload.brand_drift_score > 0.5,
            },
        )
        return {"ok": True, "data": decision.model_dump(), "error": None}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/api/v1/avatar/governance/rollback/{avatar_id}",
    response_model=dict[str, Any],
)
async def rollback_avatar(
    avatar_id: str,
    payload: AvatarRollbackRequest,
    db: Session = Depends(get_db),
):
    """Force-apply a governance action (rollback/cooldown/reactivate/block)."""
    try:
        policy = _governance.get_policy_state(db, avatar_id=avatar_id)
        from_state = policy.state if policy else "candidate"

        if payload.action == "rollback":
            new_state = _rollback.rollback(
                db,
                avatar_id=avatar_id,
                from_state=from_state,
                reason_code=payload.reason_code,
                reason_text=payload.reason_text,
            )
        elif payload.action == "cooldown":
            new_state = _rollback.cooldown(
                db,
                avatar_id=avatar_id,
                from_state=from_state,
                reason_code=payload.reason_code,
                reason_text=payload.reason_text,
            )
        elif payload.action == "reactivate":
            new_state = _rollback.reactivate(
                db,
                avatar_id=avatar_id,
                reason_code=payload.reason_code,
            )
        elif payload.action == "block":
            from app.models.avatar_policy_state import AvatarPolicyState
            row = db.query(AvatarPolicyState).filter(
                AvatarPolicyState.avatar_id == avatar_id
            ).first()
            if row is None:
                row = AvatarPolicyState(avatar_id=avatar_id)
                db.add(row)
            row.state = "blocked"
            db.commit()
            new_state = "blocked"
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown action: {payload.action!r}. Valid: rollback, cooldown, reactivate, block",
            )

        decision = AvatarPromotionDecision(
            avatar_id=avatar_id,
            action=payload.action,
            reason_code=payload.reason_code,
            previous_state=from_state,
            new_state=new_state,
            evidence={},
        )
        return {"ok": True, "data": decision.model_dump(), "error": None}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
