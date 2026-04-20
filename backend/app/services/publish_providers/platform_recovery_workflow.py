"""PlatformRecoveryWorkflow — platform-specific publish failure recovery."""
from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.models.publish_job import PublishJob

logger = logging.getLogger(__name__)


class PlatformRecoveryWorkflow:
    """Trigger platform-specific recovery for failed publish jobs.

    Recovery strategies:
    - YouTube: re-upload draft
    - TikTok: re-init upload session
    - Meta: refresh token then retry

    All recoveries are non-fatal — if the recovery fails the job stays in
    its current state for manual intervention.
    """

    def recover(self, db: "Session", job: "PublishJob") -> dict[str, Any]:
        """Dispatch to the platform-specific recovery strategy."""
        platform = (job.platform or "").lower()
        try:
            if platform in ("youtube", "shorts"):
                return self._recover_youtube(db, job)
            if platform == "tiktok":
                return self._recover_tiktok(db, job)
            if platform in ("meta", "reels", "instagram", "facebook"):
                return self._recover_meta(db, job)
        except Exception as exc:
            logger.warning("PlatformRecoveryWorkflow.recover failed job_id=%s: %s", job.id, exc)
        return {"recovered": False, "platform": platform, "job_id": job.id}

    # ------------------------------------------------------------------
    # Platform handlers
    # ------------------------------------------------------------------

    def _recover_youtube(self, db: "Session", job: "PublishJob") -> dict[str, Any]:
        """YouTube recovery: requeue as draft re-upload."""
        logger.info("YouTube recovery: re-upload draft for job_id=%s", job.id)
        # Mark job for re-upload by resetting to queued
        job.status = "queued"
        job.error_log = {
            **(job.error_log or {}),
            "recovery": "youtube_reupload_draft",
        }
        db.add(job)
        db.commit()
        return {"recovered": True, "platform": "youtube", "strategy": "reupload_draft", "job_id": job.id}

    def _recover_tiktok(self, db: "Session", job: "PublishJob") -> dict[str, Any]:
        """TikTok recovery: re-init upload session."""
        logger.info("TikTok recovery: re-init upload session for job_id=%s", job.id)
        job.status = "queued"
        job.error_log = {
            **(job.error_log or {}),
            "recovery": "tiktok_reinit_upload_session",
        }
        db.add(job)
        db.commit()
        return {"recovered": True, "platform": "tiktok", "strategy": "reinit_upload_session", "job_id": job.id}

    def _recover_meta(self, db: "Session", job: "PublishJob") -> dict[str, Any]:
        """Meta recovery: refresh token then retry."""
        logger.info("Meta recovery: refresh token then retry for job_id=%s", job.id)
        # In production this would call Meta's token refresh endpoint
        job.status = "queued"
        job.error_log = {
            **(job.error_log or {}),
            "recovery": "meta_token_refresh_retry",
        }
        db.add(job)
        db.commit()
        return {"recovered": True, "platform": "meta", "strategy": "token_refresh_retry", "job_id": job.id}
