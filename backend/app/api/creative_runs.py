from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.creative_engine_run import CreativeEngineRun

router = APIRouter(prefix="/api/v1/creative-runs", tags=["creative-runs"])


@router.get("")
def list_creative_runs(
    engine_type: str | None = None,
    status: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List creative engine run history. Optionally filter by engine_type and/or status."""
    query = db.query(CreativeEngineRun).order_by(CreativeEngineRun.created_at.desc())
    if engine_type:
        query = query.filter(CreativeEngineRun.engine_type == engine_type)
    if status:
        query = query.filter(CreativeEngineRun.status == status)
    runs = query.limit(limit).all()
    return {"items": [_serialize(run) for run in runs]}


@router.get("/{run_id}")
def get_creative_run(run_id: str, db: Session = Depends(get_db)):
    """Get a single creative engine run by ID."""
    run = db.query(CreativeEngineRun).filter(CreativeEngineRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Creative engine run not found")
    return _serialize(run)


@router.post("/{run_id}/retry")
def retry_creative_run(run_id: str, db: Session = Depends(get_db)):
    """Re-queue a failed creative engine run.

    Creates a new run record with the same input payload and increments retry_count.
    The actual engine call must be re-triggered by the caller (or via the engine's
    API endpoint) – this endpoint only creates the lineage record.
    """
    previous = db.query(CreativeEngineRun).filter(CreativeEngineRun.id == run_id).first()
    if previous is None:
        raise HTTPException(status_code=404, detail="Creative engine run not found")
    if previous.status != "failed":
        raise HTTPException(status_code=400, detail=f"Run is '{previous.status}', not 'failed' – cannot retry")

    retry = CreativeEngineRun(
        engine_type=previous.engine_type,
        status="pending",
        input_payload=previous.input_payload,
        retry_count=(previous.retry_count or 0) + 1,
        parent_run_id=previous.id,
    )
    db.add(retry)
    db.commit()
    db.refresh(retry)
    return _serialize(retry)


def _serialize(run: CreativeEngineRun) -> dict:
    return {
        "id": run.id,
        "engine_type": run.engine_type,
        "status": run.status,
        "winner_candidate_id": run.winner_candidate_id,
        "retry_count": run.retry_count,
        "parent_run_id": run.parent_run_id,
        "error_message": run.error_message,
        "input_payload": run.input_payload,
        "candidates": run.candidates,
        "output_payload": run.output_payload,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at else None,
    }
