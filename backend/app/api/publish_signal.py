"""Publish outcome signal ingestion.

Allows external systems (analytics pipelines, webhook handlers) to push real
performance metrics back into the PerformanceLearningEngine after a video has
been live for some time.  This closes the feedback loop that publish_scheduler
opens with a neutral baseline record on job completion.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.publish_job import PublishJob
from app.schemas.publish_signal import PublishSignalRequest, PublishSignalResponse
from app.services.learning_engine import PerformanceLearningEngine

router = APIRouter(prefix="/api/v1/publish", tags=["publish"])


@router.post("/jobs/{job_id}/signal", response_model=PublishSignalResponse)
def ingest_publish_signal(
    job_id: str,
    req: PublishSignalRequest,
    db: Session = Depends(get_db),
) -> PublishSignalResponse:
    """Ingest real performance metrics for a published job.

    Overwrites the neutral baseline record written by the scheduler with the
    actual conversion signal, then marks the job ``signal_status='received'``.
    """
    job: PublishJob | None = db.query(PublishJob).filter(PublishJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail=f"Publish job '{job_id}' not found")
    if job.status != "published":
        raise HTTPException(
            status_code=409,
            detail=f"Job is not in 'published' state (current: {job.status}); cannot ingest signal",
        )

    payload: dict = job.payload or {}
    metadata: dict = payload.get("metadata") or {}
    platform = req.platform or (str(job.platform) if job.platform else None)
    market_code = req.market_code or (
        str(metadata.get("market_code")) if metadata.get("market_code") else None
    )

    engine = PerformanceLearningEngine(db=db)
    engine.record(
        video_id=job_id,
        hook_pattern=str(payload.get("hook_pattern") or payload.get("format") or "unknown"),
        cta_pattern=str(payload.get("cta_mode") or "unknown"),
        template_family=str(payload.get("content_goal") or "engagement"),
        conversion_score=req.conversion_score,
        view_count=req.view_count,
        click_through_rate=req.click_through_rate,
        platform=platform,
        market_code=market_code,
    )

    job.signal_status = "received"
    db.add(job)
    db.commit()

    return PublishSignalResponse(
        ok=True,
        job_id=job_id,
        signal_status="received",
        video_id=job_id,
        conversion_score=req.conversion_score,
    )
