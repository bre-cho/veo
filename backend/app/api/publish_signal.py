"""Publish outcome signal ingestion.

Allows external systems (analytics pipelines, webhook handlers) to push real
performance metrics back into the PerformanceLearningEngine after a video has
been live for some time.  This closes the feedback loop that publish_scheduler
opens with a neutral baseline record on job completion.

When the job payload contains a ``run_id`` field, the ingestion also updates
the corresponding ``VariantRunRecord`` so the variant brain can learn from
real outcomes.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.publish_job import PublishJob
from app.schemas.publish_signal import PublishSignalRequest, PublishSignalResponse
from app.services.learning_engine import PerformanceLearningEngine

logger = logging.getLogger(__name__)

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
    Also updates any linked ``VariantRunRecord`` with real outcome data.
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

    # --- Link outcome to variant run record when run_id is present ---
    run_id = str(payload.get("run_id") or metadata.get("run_id") or "").strip()
    if run_id:
        _update_variant_outcome(
            db=db,
            run_id=run_id,
            actual_conversion_score=req.conversion_score,
            actual_view_count=req.view_count,
            actual_ctr=req.click_through_rate,
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


def _update_variant_outcome(
    *,
    db: Session,
    run_id: str,
    actual_conversion_score: float,
    actual_view_count: int,
    actual_ctr: float,
) -> None:
    """Update the VariantRunRecord for run_id with real outcome data."""
    try:
        from app.models.variant_run_record import VariantRunRecord

        row: VariantRunRecord | None = (
            db.query(VariantRunRecord)
            .filter(VariantRunRecord.run_id == run_id)
            .first()
        )
        if row is None:
            return
        row.actual_conversion_score = actual_conversion_score
        row.actual_view_count = actual_view_count
        row.actual_ctr = actual_ctr
        row.outcome_recorded_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.add(row)
        db.commit()
    except Exception:
        logger.exception("Failed to update VariantRunRecord outcome for run_id=%s", run_id)

