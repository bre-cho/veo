"""Render quality report API endpoint.

Phase 2.4: Extended with vision quality analysis endpoint.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(prefix="/api/v1/render", tags=["render"])
# Also register under plural for backward compat
router_plural = APIRouter(prefix="/api/v1/renders", tags=["renders"])


class QualityReportResponse(BaseModel):
    render_id: str
    identity_score: float | None = None
    temporal_score: float | None = None
    resolution_score: float = 1.0
    composite_score: float | None = None
    passed: bool | None = None
    threshold: float
    # Phase 2.4: vision quality dimensions
    sharpness_score: float | None = None
    face_coverage: float | None = None
    motion_blur_estimate: float | None = None
    audio_sync_score: float | None = None
    quality_remediation_hint: str | None = None


def _build_quality_response(
    render_id: str,
    job: "PublishJob",  # type: ignore[name-defined]
) -> QualityReportResponse:
    from app.services.avatar.render_quality_gate import PUBLISH_QUALITY_THRESHOLD, RenderQualityGate

    provider: dict = (job.provider_response or {}) if hasattr(job, "provider_response") else {}
    quality_data: dict = provider.get("quality_report", {})
    provider_meta: dict = (job.provider_metadata or {}) if hasattr(job, "provider_metadata") else {}

    identity_score = quality_data.get("identity_score")
    temporal_score = quality_data.get("temporal_score")
    resolution_score = float(quality_data.get("resolution_score", 1.0))

    composite_score = None
    passed = None
    if identity_score is not None and temporal_score is not None:
        gate = RenderQualityGate()
        report = gate.evaluate(
            identity_score=float(identity_score),
            temporal_score=float(temporal_score),
            resolution_score=resolution_score,
        )
        composite_score = report.composite_score
        passed = report.passed

    return QualityReportResponse(
        render_id=render_id,
        identity_score=identity_score,
        temporal_score=temporal_score,
        resolution_score=resolution_score,
        composite_score=composite_score,
        passed=passed,
        threshold=PUBLISH_QUALITY_THRESHOLD,
        sharpness_score=provider_meta.get("sharpness_score"),
        face_coverage=provider_meta.get("face_coverage"),
        motion_blur_estimate=provider_meta.get("motion_blur_estimate"),
        audio_sync_score=provider_meta.get("audio_sync_score"),
        quality_remediation_hint=provider_meta.get("quality_remediation_hint"),
    )


@router.get("/{render_id}/quality-report", response_model=QualityReportResponse)
def get_quality_report(
    render_id: str,
    db: Session = Depends(get_db),
) -> QualityReportResponse:
    """Return the quality report for a completed render job.

    Phase 2.4: Also performs live vision analysis via RenderQualityAnalyzer
    when the render has an output URL in its payload.
    """
    from app.models.publish_job import PublishJob
    from app.services.avatar.render_quality_gate import RenderQualityAnalyzer

    job: PublishJob | None = db.query(PublishJob).filter(PublishJob.id == render_id).first()
    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Render job '{render_id}' not found",
        )

    # If we have an output URL, run live analysis and persist result
    payload = job.request_payload or {}
    output_url = str(payload.get("output_url") or payload.get("render_url") or "").strip()
    if output_url:
        try:
            analyzer = RenderQualityAnalyzer()
            analysis = analyzer.analyze(output_url)
            # Persist to provider_metadata
            meta = dict(job.provider_metadata or {})
            meta.update(analysis.get("quality_metadata", {}))
            meta["quality_remediation_hint"] = analysis.get("quality_remediation_hint")
            job.provider_metadata = meta
            db.add(job)
            db.commit()
            db.refresh(job)
        except Exception:
            pass

    return _build_quality_response(render_id, job)


# Backward-compat plural route
@router_plural.get("/{render_id}/quality-report", response_model=QualityReportResponse)
def get_quality_report_plural(
    render_id: str,
    db: Session = Depends(get_db),
) -> QualityReportResponse:
    return get_quality_report(render_id=render_id, db=db)

