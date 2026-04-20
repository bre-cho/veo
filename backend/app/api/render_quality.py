"""Render quality report API endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(prefix="/api/v1/renders", tags=["renders"])


class QualityReportResponse(BaseModel):
    render_id: str
    identity_score: float | None = None
    temporal_score: float | None = None
    resolution_score: float = 1.0
    composite_score: float | None = None
    passed: bool | None = None
    threshold: float


@router.get("/{render_id}/quality-report", response_model=QualityReportResponse)
def get_quality_report(
    render_id: str,
    db: Session = Depends(get_db),
) -> QualityReportResponse:
    """Return the quality report for a completed render job."""
    from app.models.publish_job import PublishJob
    from app.services.avatar.render_quality_gate import PUBLISH_QUALITY_THRESHOLD, RenderQualityGate

    # Try to find the publish job with matching render id in provider_response
    job: PublishJob | None = db.query(PublishJob).filter(PublishJob.id == render_id).first()
    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Render job '{render_id}' not found",
        )

    provider: dict = job.provider_response or {}
    quality_data: dict = provider.get("quality_report", {})

    identity_score = quality_data.get("identity_score")
    temporal_score = quality_data.get("temporal_score")
    resolution_score = float(quality_data.get("resolution_score", 1.0))

    if identity_score is not None and temporal_score is not None:
        gate = RenderQualityGate()
        report = gate.evaluate(
            identity_score=float(identity_score),
            temporal_score=float(temporal_score),
            resolution_score=resolution_score,
        )
        return QualityReportResponse(
            render_id=render_id,
            identity_score=report.identity_score,
            temporal_score=report.temporal_score,
            resolution_score=report.resolution_score,
            composite_score=report.composite_score,
            passed=report.passed,
            threshold=PUBLISH_QUALITY_THRESHOLD,
        )

    return QualityReportResponse(
        render_id=render_id,
        threshold=PUBLISH_QUALITY_THRESHOLD,
    )
