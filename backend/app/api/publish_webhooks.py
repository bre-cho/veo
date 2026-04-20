"""Platform webhook endpoint for final publish status callbacks.

YouTube, TikTok and Meta can call this endpoint after a video finishes
processing on their side.  The payload is platform-specific but we normalise
it to update ``PublishJob.status`` and trigger a real signal into
``PerformanceLearningEngine``.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.publish_job import PublishJob
from app.services.learning_engine import PerformanceLearningEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/publish/webhooks", tags=["publish"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class WebhookPayload(BaseModel):
    """Normalised inbound webhook from any supported platform.

    Platforms differ in their exact payload shape; callers (or a thin
    platform-specific middleware) should map fields to this schema before
    calling this endpoint.
    """

    job_id: str = Field(..., description="PublishJob.id this webhook relates to")
    provider_status: str = Field(
        ...,
        description="Platform's own status string, e.g. 'PUBLISHED', 'REJECTED', 'PROCESSING'",
    )
    # Optional real metrics — when provided they update the learning engine.
    view_count: int = Field(default=0, ge=0)
    click_through_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    conversion_score: float = Field(default=0.5, ge=0.0, le=1.0)
    platform: str | None = Field(default=None)
    market_code: str | None = Field(default=None)
    raw: dict[str, Any] = Field(default_factory=dict)


class WebhookResponse(BaseModel):
    ok: bool
    job_id: str
    new_status: str


# ---------------------------------------------------------------------------
# Status normalisation helpers
# ---------------------------------------------------------------------------

_CONFIRMED_STATUSES = frozenset(
    {
        "published", "public", "live", "success", "succeeded",
        "PUBLISHED", "PUBLIC", "LIVE", "SUCCESS", "SUCCEEDED",
    }
)

_REJECTED_STATUSES = frozenset(
    {
        "rejected", "failed", "error", "removed", "banned",
        "REJECTED", "FAILED", "ERROR", "REMOVED", "BANNED",
    }
)


def _normalise_provider_status(provider_status: str) -> str:
    if provider_status in _CONFIRMED_STATUSES:
        return "confirmed"
    if provider_status in _REJECTED_STATUSES:
        return "platform_rejected"
    return "published"  # keep existing status for intermediate states


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/{platform}", response_model=WebhookResponse)
def receive_webhook(
    platform: str,
    payload: WebhookPayload,
    db: Session = Depends(get_db),
) -> WebhookResponse:
    """Receive a final status callback from a platform and update the job.

    On ``confirmed`` status the real performance metrics (if supplied) are
    written to the learning engine to replace the neutral baseline record.
    """
    job: PublishJob | None = db.query(PublishJob).filter(PublishJob.id == payload.job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail=f"Publish job '{payload.job_id}' not found")

    new_status = _normalise_provider_status(payload.provider_status)
    job.status = new_status
    job.provider_response = {
        **(job.provider_response or {}),
        "webhook": payload.raw,
        "provider_status": payload.provider_status,
    }

    if new_status == "confirmed":
        job.signal_status = "received"
        # Write real metrics into the learning engine (overrides the 0.5 baseline)
        try:
            job_payload: dict[str, Any] = job.payload or {}
            job_metadata: dict[str, Any] = job_payload.get("metadata") or {}
            effective_platform = payload.platform or str(job.platform)
            effective_market = payload.market_code or (
                str(job_metadata.get("market_code")) if job_metadata.get("market_code") else None
            )
            engine = PerformanceLearningEngine(db=db)
            engine.record(
                video_id=job.id,
                hook_pattern=str(job_payload.get("hook_pattern") or job_payload.get("format") or "unknown"),
                cta_pattern=str(job_payload.get("cta_mode") or "unknown"),
                template_family=str(job_payload.get("content_goal") or "engagement"),
                conversion_score=payload.conversion_score,
                view_count=payload.view_count,
                click_through_rate=payload.click_through_rate,
                platform=effective_platform,
                market_code=effective_market,
            )
        except Exception:
            logger.exception("Failed to update learning engine from webhook job_id=%s", payload.job_id)

    db.add(job)
    db.commit()
    db.refresh(job)

    return WebhookResponse(ok=True, job_id=job.id, new_status=new_status)
