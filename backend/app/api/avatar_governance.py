from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.avatar_governance import AvatarOutcomePayload, AvatarPromotionDecision
from app.services.avatar.avatar_governance_engine import AvatarGovernanceEngine

router = APIRouter(prefix="/avatar/governance", tags=["avatar-governance"])


# TODO: replace with the monorepo's real DB dependency.
def get_db():  # pragma: no cover
    raise NotImplementedError("Wire get_db from your app.db.session module")


@router.post("/evaluate", response_model=AvatarPromotionDecision)
def evaluate_avatar_governance(payload: AvatarOutcomePayload, db: Session = Depends(get_db)) -> AvatarPromotionDecision:
    engine = AvatarGovernanceEngine(db)
    return engine.evaluate_avatar_outcome(payload)


@router.get("/state/{avatar_id}")
def get_avatar_policy_state(avatar_id: str, db: Session = Depends(get_db)) -> dict:
    # TODO: return serialized AvatarPolicyState + recent events.
    raise HTTPException(status_code=501, detail=f"Avatar policy state endpoint not wired yet for avatar_id={avatar_id}")
