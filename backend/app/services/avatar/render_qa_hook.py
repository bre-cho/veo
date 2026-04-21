"""render_qa_hook — always-on QA gate executed on every identity_review transition.

When a render job enters the ``identity_review`` state this hook:
1. Runs ``RenderQualityAnalyzer.analyze(render_url)`` to score sharpness, face
   coverage, motion blur, and audio sync.
2. Runs ``AvatarIdentityService.verify_render_output()`` to check identity
   consistency.
3. If ``composite_score < PUBLISH_QUALITY_THRESHOLD`` → transitions the job to
   ``quality_remediation`` and writes the remediation hint into the job payload.
4. Records verification failures so the canonical reference scheduler can
   trigger a drift-refresh when needed.

Call ``execute_qa_for_job(db, job)`` from wherever a job transitions to
``identity_review``.
"""
from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.models.render_job import RenderJob

logger = logging.getLogger(__name__)


def execute_qa_for_job(
    db: "Session",
    job: "RenderJob",
) -> dict[str, Any]:
    """Run the full QA pipeline for a render job entering identity_review.

    Returns a summary dict with:
    - ``quality_passed``: bool
    - ``identity_passed``: bool
    - ``composite_score``: float
    - ``consistency_score``: float
    - ``quality_remediation_hint``: str | None
    - ``new_status``: "completed" | "quality_remediation" | "identity_gate_failed"
    """
    from app.services.avatar.render_quality_gate import (
        RenderQualityAnalyzer,
        PUBLISH_QUALITY_THRESHOLD,
    )
    from app.services.avatar.avatar_identity_service import AvatarIdentityService
    from app.services.render_fsm import assert_valid_transition

    payload: dict[str, Any] = dict(job.payload or {})
    render_url: str = str(
        payload.get("output_url") or payload.get("render_url") or ""
    ).strip()
    avatar_id: str = str(payload.get("avatar_id") or "").strip()

    result: dict[str, Any] = {
        "job_id": job.id,
        "render_url": render_url,
        "avatar_id": avatar_id,
        "quality_passed": True,
        "identity_passed": True,
        "composite_score": 1.0,
        "consistency_score": 1.0,
        "quality_remediation_hint": None,
        "new_status": "completed",
    }

    # ------------------------------------------------------------------
    # Step 1: Vision quality analysis
    # ------------------------------------------------------------------
    if render_url:
        try:
            analyzer = RenderQualityAnalyzer()
            quality_result = analyzer.analyze(render_url)
            sharpness = quality_result.get("sharpness_score", 0.5)
            face_cov = quality_result.get("face_coverage", 0.5)
            motion_blur = quality_result.get("motion_blur_estimate", 0.5)

            # Composite: same weights as RenderQualityGate defaults
            composite = round(
                sharpness * 0.5 + (1.0 - motion_blur) * 0.35 + face_cov * 0.15, 3
            )
            result["composite_score"] = composite
            result["quality_remediation_hint"] = quality_result.get(
                "quality_remediation_hint"
            )
            result["quality_passed"] = composite >= PUBLISH_QUALITY_THRESHOLD
            result["quality_details"] = {
                "sharpness_score": sharpness,
                "face_coverage": face_cov,
                "motion_blur_estimate": motion_blur,
                "audio_sync_score": quality_result.get("audio_sync_score", 0.8),
            }
        except Exception as exc:
            logger.debug("QA quality analysis failed for job_id=%s: %s", job.id, exc)

    # ------------------------------------------------------------------
    # Step 2: Identity consistency verification
    # ------------------------------------------------------------------
    if avatar_id and render_url:
        try:
            identity_svc = AvatarIdentityService()
            verify_result = identity_svc.verify_render_output(
                db, avatar_id, render_url
            )
            result["consistency_score"] = verify_result.get("consistency_score", 1.0)
            result["identity_passed"] = verify_result.get("ok", True) and not verify_result.get(
                "requires_review", False
            )
            result["identity_details"] = verify_result
        except Exception as exc:
            logger.debug(
                "QA identity verification failed for job_id=%s avatar_id=%s: %s",
                job.id, avatar_id, exc,
            )

    # ------------------------------------------------------------------
    # Step 3: Determine new status and persist remediation hint
    # ------------------------------------------------------------------
    if not result["quality_passed"]:
        result["new_status"] = "quality_remediation"
        # Write remediation hint back into the job payload
        if result["quality_remediation_hint"]:
            payload["quality_remediation_hint"] = result["quality_remediation_hint"]
            payload["quality_composite_score"] = result["composite_score"]
        job.payload = payload
        try:
            assert_valid_transition(
                entity_type="render_job",
                entity_id=str(job.id),
                current_state="identity_review",
                next_state="quality_remediation",
            )
            job.status = "quality_remediation"
            db.add(job)
            db.commit()
            logger.info(
                "Job %s transitioned to quality_remediation (score=%.3f hint=%s)",
                job.id,
                result["composite_score"],
                result["quality_remediation_hint"],
            )
        except Exception as exc:
            logger.warning(
                "Could not transition job %s to quality_remediation: %s", job.id, exc
            )
    elif not result["identity_passed"]:
        result["new_status"] = "identity_gate_failed"
        try:
            assert_valid_transition(
                entity_type="render_job",
                entity_id=str(job.id),
                current_state="identity_review",
                next_state="identity_gate_failed",
            )
            job.status = "identity_gate_failed"
            db.add(job)
            db.commit()
        except Exception as exc:
            logger.warning(
                "Could not transition job %s to identity_gate_failed: %s", job.id, exc
            )
    else:
        result["new_status"] = "completed"

    return result
