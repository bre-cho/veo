from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.publish_job import PublishJob
from app.services.learning_engine import PerformanceLearningEngine
from app.services.publish_providers import (
    ConfigurationError,
    HttpPublishProvider,
    MetaPublishProvider,
    PublishProviderBase,
    SimulatedPublishProvider,
    TikTokPublishProvider,
    YouTubePublishProvider,
)
from app.services.publish_providers.preflight import PublishPreflightValidator
from app.services.publish_providers.campaign_budget_policy import (
    BudgetExceededError,
    CampaignBudgetPolicy,
)
from app.services.youtube_seo_orchestrator import YouTubeSEOOrchestrator

logger = logging.getLogger(__name__)
_seo_orchestrator = YouTubeSEOOrchestrator()

# ---------------------------------------------------------------------------
# Publish mode configuration
# Set PUBLISH_MODE=REAL in environment to enable actual provider calls.
# Default is SIMULATED so staging never accidentally fires real publishes.
# ---------------------------------------------------------------------------
PUBLISH_MODE_SIMULATED = "SIMULATED"
PUBLISH_MODE_REAL = "REAL"

_PUBLISH_MODE: str = os.getenv("PUBLISH_MODE", PUBLISH_MODE_SIMULATED).upper()

# Re-export for backwards compatibility
__all__ = [
    "PublishProviderBase",
    "SimulatedPublishProvider",
    "BudgetExceededError",
    "CampaignBudgetPolicy",
    "ConfigurationError",
    "PublishScheduler",
]


_PLATFORM_PROVIDER_MAP: dict[str, type[PublishProviderBase]] = {
    "youtube": YouTubePublishProvider,
    "shorts": YouTubePublishProvider,
    "tiktok": TikTokPublishProvider,
    "reels": MetaPublishProvider,
    "instagram": MetaPublishProvider,
    "meta": MetaPublishProvider,
    "facebook": MetaPublishProvider,
}


def _is_simulated() -> bool:
    return _PUBLISH_MODE != PUBLISH_MODE_REAL


def _get_provider(platform: str | None = None) -> PublishProviderBase:
    if _is_simulated():
        return SimulatedPublishProvider()
    # Route to a platform-specific adapter when one exists; fall back to generic HTTP.
    if platform:
        provider_cls = _PLATFORM_PROVIDER_MAP.get(platform.lower())
        if provider_cls is not None:
            try:
                return provider_cls()
            except ConfigurationError:
                # Platform adapter is not configured; fall back to generic HTTP.
                pass
    return HttpPublishProvider()


class PublishScheduler:
    def build_publish_queue(self, plan_items: list[dict[str, Any]], platform: str = "shorts") -> list[dict[str, Any]]:
        queue: list[dict[str, Any]] = []
        start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

        for idx, item in enumerate(plan_items, start=1):
            day_index = int(item.get("day_index", 1))
            scheduled_for = start + timedelta(days=max(day_index - 1, 0), hours=idx % 3)
            queue.append(
                {
                    "queue_index": idx,
                    "platform": platform,
                    "scheduled_for": scheduled_for.isoformat(),
                    "status": "queued",
                    "payload": item,
                }
            )

        return queue

    def create_publish_jobs(
        self,
        db: Session,
        channel_plan_id: str | None,
        plan_items: list[dict[str, Any]],
        platform: str = "shorts",
    ) -> list[PublishJob]:
        queue = self.build_publish_queue(plan_items=plan_items, platform=platform)
        publish_mode = _PUBLISH_MODE
        jobs: list[PublishJob] = []
        for item in queue:
            # Build idempotency key to prevent duplicate publishes.
            idem_key = _build_idempotency_key(
                platform=item["platform"],
                channel_plan_id=channel_plan_id,
                payload=item["payload"],
            )
            # If a job with this key already exists and was published, skip.
            existing = (
                db.query(PublishJob)
                .filter(PublishJob.idempotency_key == idem_key)
                .first()
            )
            if existing is not None:
                if existing.status == "published":
                    logger.info(
                        "Skipping duplicate publish job (idempotency_key=%s status=%s)",
                        idem_key,
                        existing.status,
                    )
                    jobs.append(existing)
                    continue

            # Parse the actual scheduled_for from the queue entry so it is
            # persisted as a real datetime rather than staying NULL.
            scheduled_for_raw = item.get("scheduled_for")
            scheduled_for: datetime | None = None
            if scheduled_for_raw:
                try:
                    scheduled_for = datetime.fromisoformat(scheduled_for_raw).replace(tzinfo=None)
                except ValueError:
                    scheduled_for = None

            job = PublishJob(
                channel_plan_id=channel_plan_id,
                platform=item["platform"],
                status="queued",
                publish_mode=publish_mode,
                scheduled_for=scheduled_for,
                request_payload=item,
                payload=item["payload"],
                retry_metadata={"retry_from_job_id": None, "previous_error": None},
                idempotency_key=idem_key,
            )
            jobs.append(job)
            db.add(job)
        db.commit()
        for job in jobs:
            db.refresh(job)
        return jobs

    def run_job(self, db: Session, job: PublishJob) -> PublishJob:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # --- Avatar policy state check (non-fatal guard) ---
        payload_meta: dict[str, Any] = ((job.payload or {}).get("metadata") or {})
        avatar_id_for_check: str | None = (
            payload_meta.get("avatar_id")
            or (job.payload or {}).get("avatar_id")
        )
        if not self._avatar_is_publishable(db, avatar_id_for_check):
            job.status = "queued"
            job.error_log = {
                "mode": job.publish_mode or _PUBLISH_MODE,
                "error": "avatar_governance_deferred",
                "avatar_id": avatar_id_for_check,
                "reason": "avatar is in cooldown or blocked state",
            }
            db.add(job)
            db.commit()
            db.refresh(job)
            raise RuntimeError(
                f"Avatar {avatar_id_for_check!r} is in cooldown or blocked; deferring publish job {job.id}"
            )

        # --- Preflight validation ---
        validator = PublishPreflightValidator()
        preflight_errors = validator.validate(job)
        if preflight_errors:
            job.preflight_status = "error"
            job.preflight_errors = preflight_errors
            job.status = "failed"
            job.failed_at = now
            job.error_log = {
                "mode": job.publish_mode or _PUBLISH_MODE,
                "error": "preflight_failed",
                "preflight_errors": preflight_errors,
            }
            db.add(job)
            db.commit()
            db.refresh(job)
            raise ValueError(f"Publish preflight failed: {preflight_errors}")
        job.preflight_status = "ok"

        # --- Campaign / platform budget check ---
        budget_policy = CampaignBudgetPolicy()
        try:
            budget_policy.check(db, job)
        except BudgetExceededError as exc:
            job.status = "failed"
            job.failed_at = now
            job.error_log = {
                "mode": job.publish_mode or _PUBLISH_MODE,
                "error": "budget_exceeded",
                "budget_reason": exc.reason,
                "budget_detail": exc.detail,
            }
            db.add(job)
            db.commit()
            db.refresh(job)
            raise

        job.payload = _seo_orchestrator.enrich_publish_payload(
            db=db,
            payload=job.payload or {},
            platform=job.platform,
        )
        provider = _get_provider(platform=job.platform)

        # --- Quota check ---
        quota = provider.check_quota()
        if not quota.get("ok", True):
            logger.warning(
                "Provider quota exhausted for platform=%s; job=%s will remain queued",
                job.platform,
                job.id,
            )
            db.add(job)
            db.commit()
            raise RuntimeError(f"Provider quota exhausted: {quota}")

        try:
            job.status = "preparing"
            job.preparing_at = now
            db.add(job)
            db.commit()

            job.status = "publishing"
            job.publishing_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.add(job)
            db.commit()

            response = provider.execute(job)
            job.status = "published"
            job.published_at = datetime.now(timezone.utc).replace(tzinfo=None)
            job.signal_status = "pending"
            job.provider_response = {
                "mode": job.publish_mode or _PUBLISH_MODE,
                "raw": response,
            }
            job.external_ids = {
                "provider_publish_id": response.get("provider_publish_id"),
            }
            db.add(job)
            db.commit()
            db.refresh(job)

            # Write-back to PerformanceLearningEngine so creative engines can
            # adapt future scoring using real publish outcomes.
            if (job.publish_mode or _PUBLISH_MODE) == PUBLISH_MODE_REAL:
                self._record_publish_outcome(job, db=db)

            # Brain Layer feedback: record publish outcome to PatternMemory
            self._record_brain_publish_feedback(job, db=db)

            # Avatar Governance: evaluate outcome and apply state transitions
            self._record_avatar_governance_feedback(job, db=db)

            return job
        except Exception as exc:
            job.status = "failed"
            job.failed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            job.error_log = {
                "mode": job.publish_mode or _PUBLISH_MODE,
                "error": str(exc),
            }
            db.add(job)
            db.commit()
            db.refresh(job)
            raise

    def get_job(self, db: Session, job_id: str) -> PublishJob | None:
        return db.query(PublishJob).filter(PublishJob.id == job_id).first()

    def list_jobs(self, db: Session, status: str | None = None, limit: int = 50) -> list[PublishJob]:
        query = db.query(PublishJob).order_by(PublishJob.created_at.desc())
        if status:
            query = query.filter(PublishJob.status == status)
        return query.limit(limit).all()

    @staticmethod
    def _record_publish_outcome(job: PublishJob, db: "Session | None" = None) -> None:
        """Write a neutral baseline record to PerformanceLearningEngine on publish.

        Uses a neutral conversion_score=0.5 instead of optimistic 1.0 so the
        signal doesn't inflate scores before real metrics arrive.  The job's
        ``signal_status`` is set to ``'pending'``, signalling that a real
        measurement should be ingested later via
        ``POST /api/v1/publish/jobs/{job_id}/signal``.
        """
        try:
            payload: dict[str, Any] = job.payload or {}
            metadata: dict[str, Any] = payload.get("metadata") or {}
            engine = PerformanceLearningEngine(db=db)
            engine.record(
                video_id=job.id,
                hook_pattern=str(payload.get("hook_pattern") or payload.get("format") or "unknown"),
                cta_pattern=str(payload.get("cta_mode") or "unknown"),
                template_family=str(payload.get("content_goal") or "engagement"),
                conversion_score=0.5,  # neutral baseline; updated when real signal arrives
                platform=str(job.platform) if job.platform else None,
                market_code=str(metadata.get("market_code")) if metadata.get("market_code") else None,
            )
        except Exception:
            pass  # Non-fatal – learning write-back must never block publish flow

    @staticmethod
    def _record_brain_publish_feedback(job: PublishJob, db: "Session | None" = None) -> None:
        """Write publish outcome to Brain PatternMemory (winner DNA)."""
        try:
            from app.services.brain.brain_feedback_service import BrainFeedbackService
            payload: dict[str, Any] = job.payload or {}
            brain_feedback = BrainFeedbackService()
            brain_feedback.record_publish_outcome(
                db,
                payload={
                    "project_id": payload.get("project_id") or (payload.get("metadata") or {}).get("project_id"),
                    "market_code": (payload.get("metadata") or {}).get("market_code"),
                    "content_goal": payload.get("content_goal"),
                    "winner_dna_summary": (
                        payload.get("winner_dna_summary")
                        or (payload.get("metadata") or {}).get("winner_dna_summary")
                        or {}
                    ),
                    "selected_template_id": (payload.get("metadata") or {}).get("selected_template_id"),
                    "selected_template_family": (payload.get("metadata") or {}).get("selected_template_family"),
                    "title": payload.get("title"),
                    "description": payload.get("description"),
                    "thumbnail_url": payload.get("thumbnail_url"),
                    "platform": job.platform,
                    "metrics": (payload.get("metadata") or {}).get("metrics") or {},
                    "avatar_id": (payload.get("metadata") or {}).get("avatar_id"),
                    "topic_class": (payload.get("metadata") or {}).get("topic_class"),
                },
                score=0.5,
            )
        except Exception:
            pass  # Non-fatal – brain write-back must never block publish flow

    @staticmethod
    def _record_avatar_governance_feedback(job: PublishJob, db: "Session | None" = None) -> None:
        """Evaluate publish outcome against avatar governance rules."""
        try:
            from app.services.avatar.avatar_governance_engine import AvatarGovernanceEngine
            payload: dict[str, Any] = job.payload or {}
            metadata: dict[str, Any] = payload.get("metadata") or {}
            avatar_id: str | None = metadata.get("avatar_id")
            if not avatar_id or db is None:
                return
            governance = AvatarGovernanceEngine()
            metrics = metadata.get("metrics") or {}
            governance.evaluate_avatar_outcome(
                db,
                avatar_id=avatar_id,
                metrics=metrics,
                context={
                    "project_id": payload.get("project_id") or metadata.get("project_id"),
                    "topic_class": metadata.get("topic_class"),
                },
            )
        except Exception:
            pass  # Non-fatal – governance must never block publish flow

    def _avatar_is_publishable(self, db: Session, avatar_id: str | None) -> bool:
        """Return True if the avatar is allowed to be published right now.

        Avatars in ``blocked`` or ``retired`` state are never publishable.
        Avatars in ``cooldown`` are only publishable once ``cooldown_until`` has
        passed.  All other states (candidate, active, priority) are publishable.
        Non-fatal: any exception defaults to True so publishing is never blocked
        by a governance DB error.
        """
        if not avatar_id:
            return True
        try:
            from app.models.avatar_policy_state import AvatarPolicyState
            policy = (
                db.query(AvatarPolicyState)
                .filter(AvatarPolicyState.avatar_id == avatar_id)
                .first()
            )
            if policy is None:
                return True
            if policy.state in ("blocked", "retired"):
                return False
            if policy.state == "cooldown" and policy.cooldown_until:
                return policy.cooldown_until <= datetime.now(timezone.utc).replace(tzinfo=None)
            return True
        except Exception:
            return True  # governance check is non-fatal

    def retry_failed_job(self, db: Session, job_id: str) -> PublishJob | None:
        previous = self.get_job(db, job_id)
        if previous is None:
            return None
        if previous.status != "failed":
            return previous

        retry_job = PublishJob(
            channel_plan_id=previous.channel_plan_id,
            platform=previous.platform,
            status="queued",
            publish_mode=previous.publish_mode or _PUBLISH_MODE,
            scheduled_for=previous.scheduled_for,
            request_payload=previous.request_payload,
            payload=previous.payload,
            retry_count=(previous.retry_count or 0) + 1,
            parent_job_id=previous.id,
            retry_metadata={
                "retry_from_job_id": previous.id,
                "previous_error": (previous.error_log or {}).get("error"),
            },
        )
        db.add(retry_job)
        db.commit()
        db.refresh(retry_job)
        return retry_job


class PublishReconciler:
    """Reconciles stale published jobs that have never received a real signal.

    Jobs that are ``published`` but whose ``signal_status`` is still ``pending``
    after ``max_age_hours`` are considered stale.  The reconciler now calls
    ``ProviderFinalStateSyncer`` to fetch the current terminal state from each
    platform before falling back to marking the job as ``stale``.
    """

    def reconcile(self, db: Session, max_age_hours: int = 24) -> list[str]:
        """Return IDs of stale jobs (signal_status='pending', older than max_age_hours).

        For each stale job:
        - Calls ``ProviderFinalStateSyncer.fetch_final_state()``
        - If confirmed published → marks job ``completed`` with ``signal_status='received'``
        - If confirmed failed → triggers ``PlatformRecoveryWorkflow``
        - Otherwise → marks ``signal_status='stale'``

        Returns a list of affected job IDs.
        """
        from app.services.publish_providers.provider_final_state_syncer import ProviderFinalStateSyncer
        from app.services.publish_providers.platform_recovery_workflow import PlatformRecoveryWorkflow

        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=max_age_hours)
        stale_jobs: list[PublishJob] = (
            db.query(PublishJob)
            .filter(
                PublishJob.status == "published",
                PublishJob.signal_status == "pending",
                PublishJob.published_at <= cutoff,
            )
            .all()
        )
        affected: list[str] = []
        syncer = ProviderFinalStateSyncer()
        recovery = PlatformRecoveryWorkflow()

        for job in stale_jobs:
            platform = str(job.platform or "")
            try:
                state = syncer.fetch_final_state(job.id, platform)
                terminal = state.get("terminal_status", "unknown")
            except Exception:
                terminal = "unknown"

            if terminal == "published":
                job.status = "completed"
                job.signal_status = "received"
                db.add(job)
                # Write-back to PerformanceLearningEngine so creative engines
                # can use reconciled publish outcomes just like live publishes.
                try:
                    PublishScheduler._record_publish_outcome(job, db=db)
                except Exception as _wb_exc:
                    logger.debug(
                        "Reconciler: learning write-back failed for job id=%s: %s",
                        job.id, _wb_exc,
                    )
                logger.info("Reconciler: auto-closed confirmed published job id=%s", job.id)
            elif terminal == "failed":
                job.signal_status = "stale"
                db.add(job)
                try:
                    recovery.recover(db, job)
                except Exception:
                    pass
                logger.warning(
                    "Reconciler: confirmed failed job id=%s — recovery triggered", job.id
                )
            else:
                job.signal_status = "stale"
                db.add(job)
                logger.warning(
                    "Stale publish job detected: id=%s platform=%s published_at=%s",
                    job.id,
                    job.platform,
                    job.published_at,
                )

            affected.append(job.id)

        if affected:
            db.commit()
        return affected



# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _build_idempotency_key(
    platform: str,
    channel_plan_id: str | None,
    payload: dict[str, Any],
) -> str:
    """Compute a stable sha256 key for a publish job to prevent duplicates.

    The key is derived from the platform, channel plan ID (if any), and the
    JSON-serialised payload so two jobs with identical content produce the same
    key regardless of insertion order.
    """
    canonical = json.dumps(
        {
            "platform": platform,
            "channel_plan_id": channel_plan_id or "",
            "payload": payload,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()[:64]
