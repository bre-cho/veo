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
from typing import Any

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




# ---------------------------------------------------------------------------
# Phase 3.4: Portfolio budget status endpoint
# ---------------------------------------------------------------------------


@router.get("/portfolio/budget-status", response_model=dict)
def portfolio_budget_status(db: Session = Depends(get_db)) -> dict:
    """Return portfolio-level budget/slot status across all active campaigns.

    Phase 3.4: Aggregates remaining slot counts per campaign per platform.
    """
    from app.models.publish_job import PublishJob
    from app.services.publish_providers.campaign_budget_policy import (
        CampaignBudgetPolicy,
        _CAMPAIGN_DAILY_LIMIT,
        _PLATFORM_DAILY_LIMIT,
        _today_utc,
    )
    from datetime import datetime, timedelta

    policy = CampaignBudgetPolicy()
    today_start = _today_utc()

    # Get all distinct campaign_ids from recent jobs
    try:
        cutoff = datetime.utcnow() - timedelta(days=1)
        recent_jobs = (
            db.query(PublishJob.campaign_id, PublishJob.platform)
            .filter(
                PublishJob.campaign_id.isnot(None),
                PublishJob.created_at >= cutoff,
            )
            .distinct()
            .all()
        )
    except Exception:
        recent_jobs = []

    campaign_platform_pairs = list({(j.campaign_id, j.platform) for j in recent_jobs if j.campaign_id})

    status: dict[str, Any] = {}
    for campaign_id, platform in campaign_platform_pairs:
        used = policy._count_today(db, today_start, channel_plan_id=campaign_id, platform=platform)
        campaign_remaining = max(0, _CAMPAIGN_DAILY_LIMIT - used)
        platform_remaining = max(0, _PLATFORM_DAILY_LIMIT - used)
        key = f"{campaign_id}::{platform}"
        status[key] = {
            "campaign_id": campaign_id,
            "platform": platform,
            "used_today": used,
            "campaign_daily_limit": _CAMPAIGN_DAILY_LIMIT,
            "platform_daily_limit": _PLATFORM_DAILY_LIMIT,
            "campaign_slots_remaining": campaign_remaining,
            "platform_slots_remaining": platform_remaining,
        }

    return {"portfolio_budget_status": status, "total_campaigns": len(status)}

