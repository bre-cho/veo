from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.optimization_run import OptimizationRun
from app.schemas.optimization import OptimizationInput, OptimizationResponse
from app.services.optimization_engine import OptimizationEngine

router = APIRouter(prefix="/api/v1/optimization", tags=["optimization"])

_engine = OptimizationEngine()


class RewritePreviewRequest(BaseModel):
    preview_payload: dict
    optimization_response: OptimizationResponse | dict


@router.post("/analyze", response_model=OptimizationResponse)
def analyze_optimization(payload: OptimizationInput, db: Session = Depends(get_db)) -> OptimizationResponse:
    return _engine.analyze_and_persist(db, payload)


@router.post("/rewrite-preview")
def rewrite_preview(req: RewritePreviewRequest):
    updated = _engine.rewrite_preview_payload(req.preview_payload, req.optimization_response)
    return {"preview_payload": updated}


@router.get("/history")
def list_optimization_history(
    status: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(OptimizationRun).order_by(OptimizationRun.created_at.desc())
    if status:
        query = query.filter(OptimizationRun.status == status)
    runs = query.limit(limit).all()
    return {"items": [_serialize_run(run) for run in runs]}


@router.get("/history/{run_id}")
def get_optimization_history(run_id: str, db: Session = Depends(get_db)):
    run = db.query(OptimizationRun).filter(OptimizationRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Optimization run not found")
    return _serialize_run(run)


@router.post("/history/{run_id}/retry", response_model=OptimizationResponse)
def retry_optimization_history(run_id: str, db: Session = Depends(get_db)):
    previous = db.query(OptimizationRun).filter(OptimizationRun.id == run_id).first()
    if previous is None:
        raise HTTPException(status_code=404, detail="Optimization run not found")
    if previous.input_payload is None:
        raise HTTPException(status_code=400, detail="Cannot retry run without input payload")
    retry_count = int(previous.retry_count or 0) + 1
    payload = OptimizationInput(**previous.input_payload)
    return _engine.analyze_and_persist(db, payload, parent_run_id=previous.id, retry_count=retry_count)


def _serialize_run(run: OptimizationRun) -> dict:
    return {
        "id": run.id,
        "project_id": run.project_id,
        "render_job_id": run.render_job_id,
        "status": run.status,
        "retry_count": run.retry_count,
        "parent_run_id": run.parent_run_id,
        "input_payload": run.input_payload,
        "output_payload": run.output_payload,
        "score_summary": run.score_summary,
        "error_message": run.error_message,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at else None,
    }
