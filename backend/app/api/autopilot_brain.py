from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.autopilot_brain import AutopilotBrainCompileRequest, AutopilotBrainCompileResponse
from app.services.autopilot_brain_runtime import AutopilotBrainRuntime

router = APIRouter(prefix="/api/v1/autopilot/brain", tags=["autopilot-brain"])

_runtime = AutopilotBrainRuntime()


@router.post("/compile", response_model=AutopilotBrainCompileResponse)
def compile_brain(req: AutopilotBrainCompileRequest, db: Session = Depends(get_db)) -> AutopilotBrainCompileResponse:
    try:
        return _runtime.compile(db=db, req=req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
