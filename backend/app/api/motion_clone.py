from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.motion_clone import MotionCloneRequest, MotionCloneResponse
from app.services.motion_clone_engine import MotionCloneEngine

router = APIRouter(prefix="/api/v1/motion-clone", tags=["motion-clone"])

_engine = MotionCloneEngine()


@router.post("/plan", response_model=MotionCloneResponse)
def plan_motion_clone(req: MotionCloneRequest, db: Session = Depends(get_db)) -> MotionCloneResponse:
    return _engine.plan(req, db=db)
