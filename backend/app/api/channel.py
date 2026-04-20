from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.channel_plan import ChannelPlan
from app.schemas.channel import ChannelPlanRequest, ChannelPlanResponse
from app.services.channel_engine import ChannelEngine
from app.services.publish_scheduler import PublishScheduler

router = APIRouter(prefix="/api/v1/channel", tags=["channel"])

_engine = ChannelEngine()
_scheduler = PublishScheduler()


@router.post("/generate-plan", response_model=ChannelPlanResponse)
def generate_channel_plan(req: ChannelPlanRequest, db: Session = Depends(get_db)) -> ChannelPlanResponse:
    return _engine.generate_plan_and_persist(db, req)


@router.post("/build-publish-queue")
def build_publish_queue(
    channel_plan: ChannelPlanResponse,
    platform: str = "shorts",
    db: Session = Depends(get_db),
):
    jobs = _scheduler.create_publish_jobs(
        db=db,
        channel_plan_id=channel_plan.plan_id,
        plan_items=[item.model_dump() for item in channel_plan.series_plan],
        platform=platform,
    )
    return {"publish_jobs": [_serialize_publish_job(job) for job in jobs], "publish_queue_count": len(jobs)}


@router.get("/history")
def list_channel_history(status: str | None = None, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(ChannelPlan).order_by(ChannelPlan.created_at.desc())
    if status:
        query = query.filter(ChannelPlan.status == status)
    plans = query.limit(limit).all()
    return {"items": [_serialize_plan(plan) for plan in plans]}


@router.get("/history/{plan_id}")
def get_channel_history(plan_id: str, db: Session = Depends(get_db)):
    plan = db.query(ChannelPlan).filter(ChannelPlan.id == plan_id).first()
    if plan is None:
        raise HTTPException(status_code=404, detail="Channel plan not found")
    return _serialize_plan(plan)


@router.post("/history/{plan_id}/retry", response_model=ChannelPlanResponse)
def retry_channel_history(plan_id: str, db: Session = Depends(get_db)):
    previous = db.query(ChannelPlan).filter(ChannelPlan.id == plan_id).first()
    if previous is None:
        raise HTTPException(status_code=404, detail="Channel plan not found")
    request_context = previous.request_context or {}
    retry_count = int(previous.retry_count or 0) + 1
    req = ChannelPlanRequest(**request_context)
    return _engine.generate_plan_and_persist(db, req, parent_plan_id=previous.id, retry_count=retry_count)


@router.get("/publish-jobs")
def list_publish_jobs(status: str | None = None, limit: int = 50, db: Session = Depends(get_db)):
    jobs = _scheduler.list_jobs(db, status=status, limit=limit)
    return {"items": [_serialize_publish_job(job) for job in jobs]}


@router.get("/publish-jobs/{job_id}")
def get_publish_job(job_id: str, db: Session = Depends(get_db)):
    job = _scheduler.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Publish job not found")
    return _serialize_publish_job(job)


@router.post("/publish-jobs/{job_id}/run")
def run_publish_job(job_id: str, db: Session = Depends(get_db)):
    job = _scheduler.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Publish job not found")
    updated = _scheduler.run_job(db, job)
    return _serialize_publish_job(updated)


@router.post("/publish-jobs/{job_id}/retry")
def retry_publish_job(job_id: str, db: Session = Depends(get_db)):
    job = _scheduler.retry_failed_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Publish job not found")
    return _serialize_publish_job(job)


def _serialize_plan(plan: ChannelPlan) -> dict:
    return {
        "id": plan.id,
        "project_id": plan.project_id,
        "avatar_id": plan.avatar_id,
        "product_id": plan.product_id,
        "status": plan.status,
        "channel_name": plan.channel_name,
        "niche": plan.niche,
        "market_code": plan.market_code,
        "goal": plan.goal,
        "retry_count": plan.retry_count,
        "parent_plan_id": plan.parent_plan_id,
        "request_context": plan.request_context,
        "selected_variants": plan.selected_variants,
        "ranking_scores": plan.ranking_scores,
        "final_plan": plan.final_plan,
        "error_message": plan.error_message,
        "started_at": plan.started_at.isoformat() if plan.started_at else None,
        "completed_at": plan.completed_at.isoformat() if plan.completed_at else None,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
    }


def _serialize_publish_job(job) -> dict:
    return {
        "id": job.id,
        "channel_plan_id": job.channel_plan_id,
        "platform": job.platform,
        "publish_mode": getattr(job, "publish_mode", "SIMULATED"),
        "status": job.status,
        "retry_count": job.retry_count,
        "parent_job_id": job.parent_job_id,
        "scheduled_for": job.scheduled_for.isoformat() if job.scheduled_for else None,
        "request_payload": job.request_payload,
        "provider_response": job.provider_response,
        "external_ids": job.external_ids,
        "error_log": job.error_log,
        "retry_metadata": job.retry_metadata,
        "queued_at": job.queued_at.isoformat() if job.queued_at else None,
        "preparing_at": job.preparing_at.isoformat() if job.preparing_at else None,
        "publishing_at": job.publishing_at.isoformat() if job.publishing_at else None,
        "published_at": job.published_at.isoformat() if job.published_at else None,
        "failed_at": job.failed_at.isoformat() if job.failed_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }
