"""Factory pipeline API routes.

Endpoints
---------
POST /api/v1/factory/run                         – start a new factory run
GET  /api/v1/factory/runs/{run_id}               – get run detail
POST /api/v1/factory/runs/{run_id}/approve       – approve paused run
POST /api/v1/factory/runs/{run_id}/retry         – re-enqueue failed run
POST /api/v1/factory/runs/{run_id}/cancel        – cancel a pending/running run
GET  /api/v1/factory/runs/{run_id}/timeline      – stage timeline
GET  /api/v1/factory/runs/{run_id}/metrics       – metric events
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.factory.factory_context import FactoryContext
from app.factory.factory_orchestrator import FactoryOrchestrator
from app.factory.factory_state import RunStatus
from app.models.factory_run import (
    FactoryIncident,
    FactoryMetricEvent,
    FactoryQualityGate,
    FactoryRun,
    FactoryRunStage,
)
from app.schemas.factory import (
    FactoryRunDetailOut,
    FactoryRunOut,
    FactoryRunRequest,
    MetricsOut,
    MetricOut,
    StageOut,
    TimelineOut,
)
from app.workers.factory_worker import factory_run_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/factory", tags=["factory"])


# ---------------------------------------------------------------------------
# POST /run  – start a new run
# ---------------------------------------------------------------------------

@router.post("/run", response_model=FactoryRunOut, status_code=status.HTTP_202_ACCEPTED)
def start_factory_run(
    req: FactoryRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> FactoryRunOut:
    """Create a FactoryRun record and dispatch it to the Celery worker."""
    ctx = FactoryContext(
        input_type=req.input_type,
        input_topic=req.input_topic,
        input_script=req.input_script,
        input_avatar_id=req.input_avatar_id,
        input_series_id=req.input_series_id,
        project_id=req.project_id,
        budget_cents=req.budget_cents,
    )
    orchestrator = FactoryOrchestrator(db)
    run = orchestrator.start_run(ctx)
    # Dispatch async execution
    background_tasks.add_task(_dispatch_factory_run, run.id)
    return FactoryRunOut.model_validate(run)


def _dispatch_factory_run(run_id: str) -> None:
    """Enqueue the Celery task (best-effort; errors are logged)."""
    try:
        factory_run_task.delay(run_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not enqueue factory_run_task for %s: %s", run_id, exc)


# ---------------------------------------------------------------------------
# GET /runs/{run_id}
# ---------------------------------------------------------------------------

@router.get("/runs/{run_id}", response_model=FactoryRunDetailOut)
def get_factory_run(run_id: str, db: Session = Depends(get_db)) -> FactoryRunDetailOut:
    run = _get_or_404(db, run_id)
    stages = (
        db.query(FactoryRunStage)
        .filter(FactoryRunStage.run_id == run_id)
        .order_by(FactoryRunStage.stage_index)
        .all()
    )
    gates = (
        db.query(FactoryQualityGate)
        .filter(FactoryQualityGate.run_id == run_id)
        .all()
    )
    incidents = (
        db.query(FactoryIncident)
        .filter(FactoryIncident.run_id == run_id)
        .all()
    )
    out = FactoryRunDetailOut.model_validate(run)
    out.stages = [StageOut.model_validate(s) for s in stages]
    out.quality_gates = [
        __import__("app.schemas.factory", fromlist=["QualityGateOut"]).QualityGateOut.model_validate(g)
        for g in gates
    ]
    out.incidents = [
        __import__("app.schemas.factory", fromlist=["IncidentOut"]).IncidentOut.model_validate(i)
        for i in incidents
    ]
    return out


# ---------------------------------------------------------------------------
# POST /runs/{run_id}/approve
# ---------------------------------------------------------------------------

@router.post("/runs/{run_id}/approve", response_model=FactoryRunOut)
def approve_factory_run(run_id: str, db: Session = Depends(get_db)) -> FactoryRunOut:
    run = _get_or_404(db, run_id)
    if run.status != RunStatus.AWAITING_APPROVAL.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run is not awaiting approval (status={run.status})",
        )
    run.status = RunStatus.RUNNING.value
    db.commit()
    _dispatch_factory_run(run_id)
    return FactoryRunOut.model_validate(run)


# ---------------------------------------------------------------------------
# POST /runs/{run_id}/retry
# ---------------------------------------------------------------------------

@router.post("/runs/{run_id}/retry", response_model=FactoryRunOut)
def retry_factory_run(run_id: str, db: Session = Depends(get_db)) -> FactoryRunOut:
    run = _get_or_404(db, run_id)
    if run.status not in (RunStatus.FAILED.value, RunStatus.CANCELLED.value):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run cannot be retried (status={run.status})",
        )
    run.status = RunStatus.PENDING.value
    run.blocking_reason = None
    run.error_detail = None
    db.commit()
    _dispatch_factory_run(run_id)
    return FactoryRunOut.model_validate(run)


# ---------------------------------------------------------------------------
# POST /runs/{run_id}/cancel
# ---------------------------------------------------------------------------

@router.post("/runs/{run_id}/cancel", response_model=FactoryRunOut)
def cancel_factory_run(run_id: str, db: Session = Depends(get_db)) -> FactoryRunOut:
    run = _get_or_404(db, run_id)
    if run.status in (RunStatus.COMPLETED.value, RunStatus.CANCELLED.value):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run is already terminal (status={run.status})",
        )
    run.status = RunStatus.CANCELLED.value
    db.commit()
    return FactoryRunOut.model_validate(run)


# ---------------------------------------------------------------------------
# GET /runs/{run_id}/timeline
# ---------------------------------------------------------------------------

@router.get("/runs/{run_id}/timeline", response_model=TimelineOut)
def get_factory_run_timeline(run_id: str, db: Session = Depends(get_db)) -> TimelineOut:
    _get_or_404(db, run_id)
    stages = (
        db.query(FactoryRunStage)
        .filter(FactoryRunStage.run_id == run_id)
        .order_by(FactoryRunStage.stage_index)
        .all()
    )
    return TimelineOut(run_id=run_id, stages=[StageOut.model_validate(s) for s in stages])


# ---------------------------------------------------------------------------
# GET /runs/{run_id}/metrics
# ---------------------------------------------------------------------------

@router.get("/runs/{run_id}/metrics", response_model=MetricsOut)
def get_factory_run_metrics(run_id: str, db: Session = Depends(get_db)) -> MetricsOut:
    _get_or_404(db, run_id)
    metrics = (
        db.query(FactoryMetricEvent)
        .filter(FactoryMetricEvent.run_id == run_id)
        .order_by(FactoryMetricEvent.recorded_at)
        .all()
    )
    return MetricsOut(run_id=run_id, metrics=[MetricOut.model_validate(m) for m in metrics])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_or_404(db: Session, run_id: str) -> FactoryRun:
    run = db.query(FactoryRun).filter(FactoryRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail=f"Factory run {run_id} not found")
    return run
