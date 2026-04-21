"""PlatformRecoveryWorkflow — platform-specific publish failure recovery.

Phase 3.3: Added escalation chain (queued → retry_1 → retry_2 → human_review)
and recovery_metadata tracking.

Phase 3.5 (v16): Added ``FailureClassifier`` for structured error classification
and richer per-provider recovery choreography:
- YouTube: auth_expired → refresh_oauth; quota_exceeded → defer_24h;
           content_rejected → flag_for_review; network_error → immediate_retry
- TikTok:  auth_expired → reinit_session; rate_limited → backoff_retry;
           content_policy → flag_for_review; network_error → immediate_retry
- Meta:    token_expired → token_refresh; policy_violation → content_review;
           account_restricted → escalate_account_ops; rate_limited → defer_1h
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

# ---------------------------------------------------------------------------
# Phase 3.5: Error classification taxonomy
# ---------------------------------------------------------------------------

# Error code groups per platform
_YOUTUBE_ERROR_CODES: dict[str, str] = {
    "401": "auth_expired",
    "403": "quota_exceeded",
    "400": "content_rejected",
    "429": "rate_limited",
    "5": "network_error",  # 5xx prefix
}
_TIKTOK_ERROR_CODES: dict[str, str] = {
    "10002": "auth_expired",
    "10003": "auth_expired",
    "10005": "content_policy",
    "10006": "rate_limited",
    "5": "network_error",
}
_META_ERROR_CODES: dict[str, str] = {
    "190": "token_expired",
    "200": "policy_violation",
    "275": "policy_violation",
    "368": "account_restricted",
    "613": "rate_limited",
    "5": "network_error",
}


class FailureClassifier:
    """Classify a publish failure into a structured error type.

    Reads the ``error_log`` on a job and returns a dict with:
    - ``error_type``: str — e.g. "auth_expired", "rate_limited", "content_policy"
    - ``error_code``: str | None — raw platform error code
    - ``recoverable``: bool — whether auto-recovery is likely to help
    - ``suggested_strategy``: str — recommended recovery action
    """

    def classify(
        self,
        job: "PublishJob",
        platform: str,
    ) -> dict[str, Any]:
        """Classify the failure on ``job`` for ``platform``."""
        error_log = dict(job.error_log or {})
        raw_code = str(error_log.get("error_code") or error_log.get("code") or "")
        provider_meta: dict = dict(
            (getattr(job, "provider_metadata", None) or {})
        )

        error_type = self._classify_code(raw_code, platform)

        # Check policy_violation_codes from provider metadata
        if not error_type and provider_meta.get("policy_violation_codes"):
            error_type = "policy_violation"
        if not error_type and provider_meta.get("rejection_reason"):
            error_type = "content_policy"

        if not error_type:
            error_type = "unknown"

        recoverable = error_type not in ("content_rejected", "account_restricted")
        strategy = self._strategy(error_type, platform)

        return {
            "error_type": error_type,
            "error_code": raw_code or None,
            "recoverable": recoverable,
            "suggested_strategy": strategy,
        }

    @staticmethod
    def _classify_code(raw_code: str, platform: str) -> str | None:
        """Map a raw error code string to a structured error type."""
        plat = platform.lower()
        code_map = (
            _YOUTUBE_ERROR_CODES if plat in ("youtube", "shorts")
            else _TIKTOK_ERROR_CODES if plat == "tiktok"
            else _META_ERROR_CODES if plat in ("meta", "reels", "instagram", "facebook")
            else {}
        )
        # Exact match
        if raw_code in code_map:
            return code_map[raw_code]
        # Prefix match (e.g. "5xx" network errors)
        for prefix, etype in code_map.items():
            if raw_code.startswith(prefix):
                return etype
        return None

    @staticmethod
    def get_strategy_for_error_type(error_type: str, platform: str) -> str:
        """Public API: return the recommended recovery strategy for an error type."""
        _STRATEGIES: dict[str, str] = {
            "auth_expired": "refresh_oauth_then_retry",
            "quota_exceeded": "defer_24h",
            "content_rejected": "flag_for_review",
            "content_policy": "flag_for_review",
            "network_error": "immediate_retry",
            "rate_limited": "backoff_retry",
            "token_expired": "token_refresh_retry",
            "policy_violation": "resubmit_with_modified_content",
            "account_restricted": "escalate_account_ops",
            "unknown": "escalate_to_human_review",
        }
        return _STRATEGIES.get(error_type, "escalate_to_human_review")

    @staticmethod
    def _strategy(error_type: str, platform: str) -> str:
        """Return the recommended recovery strategy for an error type."""
        return FailureClassifier.get_strategy_for_error_type(error_type, platform)


class PlatformRecoveryWorkflow:
    """Trigger platform-specific recovery for failed publish jobs.

    Phase 3.3: Escalation chain:
    queued -> retry_1 -> retry_2 -> human_review (no infinite loop)

    Phase 3.5 (v16): Uses FailureClassifier to derive error type and
    route to the optimal recovery choreography per provider.

    All recoveries are non-fatal -- if the recovery fails the job stays in
    its current state for manual intervention.
    """

    def __init__(self) -> None:
        self._classifier = FailureClassifier()

    def recover(self, db: "Session", job: "PublishJob") -> dict[str, Any]:
        """Dispatch to the platform-specific recovery strategy.

        Phase 3.5: Classifies the error first, then routes to the optimal
        recovery strategy based on error type and platform.
        """
        platform = (job.platform or "").lower()
        error_log = dict(job.error_log or {})
        recovery_meta = dict(error_log.get("recovery_metadata", {}))
        attempt_count = int(recovery_meta.get("attempt_count", 0)) + 1

        # Classify the failure (Phase 3.5)
        classification = self._classifier.classify(job, platform)
        error_type = classification["error_type"]
        recoverable = classification["recoverable"]

        # Escalation: after _MAX_RETRIES or non-recoverable, move to human_review
        if attempt_count > _MAX_RETRIES or not recoverable:
            job.status = "human_review"
            recovery_meta["attempt_count"] = attempt_count
            recovery_meta["last_recovery_strategy"] = "escalated_to_human_review"
            recovery_meta["escalated_at"] = time.time()
            recovery_meta["error_type"] = error_type
            error_log["recovery_metadata"] = recovery_meta
            job.error_log = error_log
            db.add(job)
            db.commit()
            logger.info(
                "Recovery escalated to human_review after %d attempts job_id=%s error_type=%s",
                attempt_count, job.id, error_type,
            )
            return {
                "recovered": False,
                "platform": platform,
                "job_id": job.id,
                "status": "human_review",
                "attempt_count": attempt_count,
                "error_type": error_type,
            }

        # Compute next retry stage label
        stage_label = f"retry_{attempt_count}" if attempt_count < _MAX_RETRIES else "retry_final"
        next_retry_at = time.time() + _RETRY_INTERVALS[min(attempt_count - 1, len(_RETRY_INTERVALS) - 1)]

        try:
            if platform in ("youtube", "shorts"):
                result = self._recover_youtube(db, job, attempt_count=attempt_count, error_type=error_type)
            elif platform == "tiktok":
                result = self._recover_tiktok(db, job, attempt_count=attempt_count, error_type=error_type)
            elif platform in ("meta", "reels", "instagram", "facebook"):
                result = self._recover_meta(db, job, attempt_count=attempt_count, error_type=error_type)
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
        recovery_meta["error_type"] = error_type
        error_log = dict(job.error_log or {})
        error_log["recovery_metadata"] = recovery_meta
        job.error_log = error_log
        db.add(job)
        db.commit()

        return {**result, "attempt_count": attempt_count, "recovery_metadata": recovery_meta}

    # ------------------------------------------------------------------
    # Platform handlers (Phase 3.5: error_type-aware routing)
    # ------------------------------------------------------------------

    def _recover_youtube(
        self,
        db: "Session",
        job: "PublishJob",
        attempt_count: int = 1,
        error_type: str = "unknown",
    ) -> dict[str, Any]:
        """YouTube recovery: route by error_type."""
        strategy_map: dict[str, str] = {
            "auth_expired": "refresh_oauth_then_retry",
            "quota_exceeded": "defer_24h",
            "content_rejected": "flag_for_review",
            "network_error": "immediate_retry",
            "rate_limited": "backoff_retry",
        }
        strategy = strategy_map.get(error_type)
        if not strategy:
            strategy = "refresh_oauth_then_retry" if attempt_count == 1 else "reupload_draft"

        logger.info("YouTube recovery: strategy=%s job_id=%s", strategy, job.id)
        if strategy == "defer_24h":
            job.status = "deferred"
        elif strategy == "flag_for_review":
            job.status = "human_review"
        else:
            job.status = "queued"
        db.add(job)
        db.commit()
        return {"recovered": strategy != "flag_for_review", "platform": "youtube", "strategy": strategy, "job_id": job.id}

    def _recover_tiktok(
        self,
        db: "Session",
        job: "PublishJob",
        attempt_count: int = 1,
        error_type: str = "unknown",
    ) -> dict[str, Any]:
        """TikTok recovery: route by error_type."""
        strategy_map: dict[str, str] = {
            "auth_expired": "reinit_session",
            "rate_limited": "backoff_retry",
            "content_policy": "flag_for_review",
            "network_error": "immediate_retry",
        }
        strategy = strategy_map.get(error_type, "reinit_upload_session")
        logger.info("TikTok recovery: strategy=%s job_id=%s", strategy, job.id)
        if strategy == "flag_for_review":
            job.status = "human_review"
        else:
            job.status = "queued"
        db.add(job)
        db.commit()
        return {"recovered": strategy != "flag_for_review", "platform": "tiktok", "strategy": strategy, "job_id": job.id}

    def _recover_meta(
        self,
        db: "Session",
        job: "PublishJob",
        attempt_count: int = 1,
        error_type: str = "unknown",
    ) -> dict[str, Any]:
        """Meta recovery: route by error_type."""
        strategy_map: dict[str, str] = {
            "token_expired": "token_refresh_retry",
            "policy_violation": "resubmit_with_modified_content",
            "account_restricted": "escalate_account_ops",
            "rate_limited": "defer_1h",
            "network_error": "immediate_retry",
        }
        # Also check provider_metadata for legacy policy_violation_codes
        provider_meta: dict = dict(getattr(job, "provider_metadata", None) or {})
        if not strategy_map.get(error_type) and provider_meta.get("policy_violation_codes"):
            error_type = "policy_violation"

        strategy = strategy_map.get(error_type, "token_refresh_retry")
        logger.info("Meta recovery: strategy=%s job_id=%s", strategy, job.id)
        if strategy in ("escalate_account_ops",):
            job.status = "human_review"
        elif strategy == "defer_1h":
            job.status = "deferred"
        else:
            job.status = "queued"
        db.add(job)
        db.commit()
        return {"recovered": strategy not in ("escalate_account_ops",), "platform": "meta", "strategy": strategy, "job_id": job.id}

