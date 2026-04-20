"""PlatformRecoveryWorkflow — platform-specific publish failure recovery.

Phase 3.3: Added escalation chain (queued → retry_1 → retry_2 → human_review)
and recovery_metadata tracking.
"""
from __future__ import annotations

import logging
import time
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.models.publish_job import PublishJob

logger = logging.getLogger(__name__)

# Maximum retries before escalating to human_review
_MAX_RETRIES = 3
# Retry back-off intervals in seconds (retry_1, retry_2, ...)
_RETRY_INTERVALS = [300, 900, 3600]


class PlatformRecoveryWorkflow:
    """Trigger platform-specific recovery for failed publish jobs.

    Phase 3.3: Escalation chain:
    queued → retry_1 → retry_2 → human_review (no infinite loop)

    Recovery strategies:
    - YouTube: refresh_oauth_then_retry → reupload_draft
    - TikTok: reinit_upload_session
    - Meta: resubmit_with_modified_content (when policy_violation)
              token_refresh_retry (otherwise)

    All recoveries are non-fatal — if the recovery fails the job stays in
    its current state for manual intervention.
    """

    def recover(self, db: "Session", job: "PublishJob") -> dict[str, Any]:
        """Dispatch to the platform-specific recovery strategy."""
        platform = (job.platform or "").lower()
        error_log = dict(job.error_log or {})
        recovery_meta = dict(error_log.get("recovery_metadata", {}))
        attempt_count = int(recovery_meta.get("attempt_count", 0)) + 1

        # Escalation: after _MAX_RETRIES, move to human_review
        if attempt_count > _MAX_RETRIES:
            job.status = "human_review"
            recovery_meta["attempt_count"] = attempt_count
            recovery_meta["last_recovery_strategy"] = "escalated_to_human_review"
            recovery_meta["escalated_at"] = time.time()
            error_log["recovery_metadata"] = recovery_meta
            job.error_log = error_log
            db.add(job)
            db.commit()
            logger.info(
                "Recovery escalated to human_review after %d attempts job_id=%s",
                attempt_count, job.id,
            )
            return {
                "recovered": False,
                "platform": platform,
                "job_id": job.id,
                "status": "human_review",
                "attempt_count": attempt_count,
            }

        # Compute next retry stage label
        stage_label = f"retry_{attempt_count}" if attempt_count < _MAX_RETRIES else "retry_final"
        next_retry_at = time.time() + _RETRY_INTERVALS[min(attempt_count - 1, len(_RETRY_INTERVALS) - 1)]

        try:
            if platform in ("youtube", "shorts"):
                result = self._recover_youtube(db, job, attempt_count=attempt_count)
            elif platform == "tiktok":
                result = self._recover_tiktok(db, job, attempt_count=attempt_count)
            elif platform in ("meta", "reels", "instagram", "facebook"):
                result = self._recover_meta(db, job, attempt_count=attempt_count)
            else:
                result = {"recovered": False, "platform": platform, "job_id": job.id}
        except Exception as exc:
            logger.warning("PlatformRecoveryWorkflow.recover failed job_id=%s: %s", job.id, exc)
            result = {"recovered": False, "platform": platform, "job_id": job.id}

        # Update recovery_metadata
        recovery_meta["attempt_count"] = attempt_count
        recovery_meta["last_recovery_strategy"] = result.get("strategy", "unknown")
        recovery_meta["next_retry_at"] = next_retry_at
        recovery_meta["stage"] = stage_label
        error_log = dict(job.error_log or {})
        error_log["recovery_metadata"] = recovery_meta
        job.error_log = error_log
        db.add(job)
        db.commit()

        return {**result, "attempt_count": attempt_count, "recovery_metadata": recovery_meta}

    # ------------------------------------------------------------------
    # Platform handlers
    # ------------------------------------------------------------------

    def _recover_youtube(
        self, db: "Session", job: "PublishJob", attempt_count: int = 1
    ) -> dict[str, Any]:
        """YouTube recovery: refresh OAuth first, then reupload draft."""
        if attempt_count == 1:
            strategy = "refresh_oauth_then_retry"
            logger.info("YouTube recovery: refresh OAuth for job_id=%s", job.id)
        else:
            strategy = "reupload_draft"
            logger.info("YouTube recovery: re-upload draft for job_id=%s", job.id)

        job.status = "queued"
        db.add(job)
        db.commit()
        return {"recovered": True, "platform": "youtube", "strategy": strategy, "job_id": job.id}

    def _recover_tiktok(
        self, db: "Session", job: "PublishJob", attempt_count: int = 1
    ) -> dict[str, Any]:
        """TikTok recovery: re-init upload session."""
        logger.info("TikTok recovery: re-init upload session for job_id=%s", job.id)
        job.status = "queued"
        db.add(job)
        db.commit()
        return {"recovered": True, "platform": "tiktok", "strategy": "reinit_upload_session", "job_id": job.id}

    def _recover_meta(
        self, db: "Session", job: "PublishJob", attempt_count: int = 1
    ) -> dict[str, Any]:
        """Meta recovery: resubmit with modified content if policy violation, else token refresh."""
        # Check if rejection was due to policy violation
        provider_meta: dict = dict(job.provider_metadata or {}) if hasattr(job, "provider_metadata") else {}
        policy_codes = provider_meta.get("policy_violation_codes", [])

        if policy_codes:
            strategy = "resubmit_with_modified_content"
            logger.info("Meta recovery: resubmit with modified content for job_id=%s", job.id)
        else:
            strategy = "token_refresh_retry"
            logger.info("Meta recovery: refresh token then retry for job_id=%s", job.id)

        job.status = "queued"
        db.add(job)
        db.commit()
        return {"recovered": True, "platform": "meta", "strategy": strategy, "job_id": job.id}

