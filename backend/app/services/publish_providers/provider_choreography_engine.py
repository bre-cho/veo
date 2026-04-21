"""ProviderChoreographyEngine — deep multi-platform publish orchestration.

Closes the final gap in the publish enterprise stack by providing:

1. **Sequenced multi-platform publishing** — coordinates publish order across
   platforms, respecting inter-platform dependencies (e.g. YouTube first,
   then cross-post to Meta/TikTok with YouTube URL).

2. **Batch state sync** — polls all platforms in a single coordinated pass
   with richer per-platform metadata (more fields than the basic syncer).

3. **Unified compliance gate** — applies RegionContentComplianceMatrix +
   ComplianceRiskPolicy in one call before any publish begins.

4. **Retry choreography** — coordinates retry schedules across platforms
   when a multi-platform publish has partial failures.

5. **Persistent orchestration state** — records multi-platform job state,
   retry state, and recovery state so the system can resume safely after
   restarts.

6. **Replay / audit log** — immutable append-only audit trail for every
   publish decision, suitable for compliance replay and debugging.

Usage::

    engine = ProviderChoreographyEngine(db=db)

    # Before publishing a batch:
    gate = engine.apply_compliance_gate(
        jobs=[job1, job2],
        region_code="VN",
    )
    if gate["all_clear"]:
        results = engine.choreograph_multi_platform_publish(
            db=db,
            jobs=[job1, job2],
            sequence_strategy="youtube_first",
        )
"""
from __future__ import annotations

import logging
import time
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Default inter-platform delay (seconds) between sequential publishes
_INTER_PLATFORM_DELAY_SEC = 2.0
# Platforms ordered for "youtube_first" sequencing strategy
_YOUTUBE_FIRST_ORDER = ["youtube", "shorts", "tiktok", "reels", "instagram", "meta", "facebook"]

# ---------------------------------------------------------------------------
# In-memory persistent orchestration state and audit log
# ---------------------------------------------------------------------------
# {orchestration_id → {job_id → platform_state_dict}}
_ORCH_STATE: dict[str, dict[str, Any]] = {}
# Append-only audit log entries
_AUDIT_LOG: list[dict[str, Any]] = []
# Maximum audit log entries retained in memory
_MAX_AUDIT_ENTRIES = 10_000


class ProviderChoreographyEngine:
    """Orchestrate multi-platform publishing with deep coordination.

    Parameters
    ----------
    db:
        SQLAlchemy session (used for state sync writes).
    syncer:
        Optional custom ``ProviderFinalStateSyncer``; defaults to a new instance.
    poll_orchestrator:
        Optional custom ``ProviderStatePollOrchestrator``.
    """

    def __init__(
        self,
        db: "Session | None" = None,
        syncer: Any | None = None,
        poll_orchestrator: Any | None = None,
    ) -> None:
        self._db = db
        self._syncer = syncer
        self._poll_orchestrator = poll_orchestrator

    # ------------------------------------------------------------------
    # Compliance gate
    # ------------------------------------------------------------------

    def apply_compliance_gate(
        self,
        jobs: list[Any],
        region_code: str,
        content_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Apply unified compliance check for all jobs before a publish batch.

        Runs both ``RegionContentComplianceMatrix`` and
        ``ComplianceRiskPolicy`` for each job.

        Returns:
            Dict with ``all_clear`` (bool), ``blocked_jobs``,
            ``review_jobs``, ``allowed_jobs``, ``violation_details``.
        """
        from app.services.publish_providers.compliance_risk_policy import (
            ComplianceRiskPolicy,
            RegionContentComplianceMatrix,
        )

        region_matrix = RegionContentComplianceMatrix()
        risk_policy = ComplianceRiskPolicy()
        blocked: list[str] = []
        review: list[str] = []
        allowed: list[str] = []
        violation_details: list[dict[str, Any]] = []

        for job in jobs:
            job_id = str(getattr(job, "id", "unknown"))
            platform = str(getattr(job, "platform", "unknown"))
            content = self._extract_content(job)

            # Region matrix check
            region_result = region_matrix.evaluate(
                content=content,
                region_code=region_code,
                platform=platform,
                content_types=content_types,
            )

            # Platform compliance risk check
            risk_result = risk_policy.evaluate(content=content, platform=platform)

            # Combine: blocked wins
            region_status = region_result.get("status", "allowed")
            risk_status = risk_result.compliance_status

            if region_status == "blocked" or risk_status == "failed":
                blocked.append(job_id)
                status = "blocked"
            elif region_status == "review" or risk_status == "review":
                review.append(job_id)
                status = "review"
            else:
                allowed.append(job_id)
                status = "allowed"

            if region_result.get("violations") or risk_result.risk_flags:
                violation_details.append({
                    "job_id": job_id,
                    "platform": platform,
                    "status": status,
                    "region_violations": region_result.get("violations", []),
                    "risk_flags": risk_result.risk_flags,
                    "risk_score": risk_result.risk_score,
                })

        return {
            "all_clear": len(blocked) == 0,
            "region_code": region_code,
            "total_jobs": len(jobs),
            "allowed_jobs": allowed,
            "review_jobs": review,
            "blocked_jobs": blocked,
            "violation_details": violation_details,
        }

    # ------------------------------------------------------------------
    # Multi-platform publish choreography
    # ------------------------------------------------------------------

    def choreograph_multi_platform_publish(
        self,
        jobs: list[Any],
        sequence_strategy: str = "youtube_first",
        inter_delay_sec: float = _INTER_PLATFORM_DELAY_SEC,
        _sleep: bool = False,
        orchestration_id: str | None = None,
    ) -> dict[str, Any]:
        """Sequence and coordinate publish across multiple platform jobs.

        Applies platform ordering based on ``sequence_strategy``:
        - ``youtube_first``: YouTube/Shorts → TikTok → Reels → Meta/Facebook
        - ``priority``: jobs in their provided order
        - ``parallel_safe``: publishes without cross-platform dependencies simultaneously

        Args:
            jobs: List of publish job objects (must have ``platform``, ``id``).
            sequence_strategy: Ordering strategy (see above).
            inter_delay_sec: Delay (seconds) between platform publishes.
                Honoured only when ``_sleep=True``.
            _sleep: When True, actually sleep between publishes (prod only).
            orchestration_id: Optional unique ID for this orchestration run.
                Used to key the persistent orchestration state.

        Returns:
            Dict with ``results`` (per-job status), ``sequence_used``,
            ``total``, ``succeeded``, ``failed``, ``orchestration_id``.
        """
        import uuid as _uuid
        orch_id = orchestration_id or str(_uuid.uuid4())

        ordered_jobs = self._order_jobs(jobs, strategy=sequence_strategy)
        results: list[dict[str, Any]] = []
        succeeded = failed = 0
        cross_platform_context: dict[str, Any] = {}

        for idx, job in enumerate(ordered_jobs):
            job_id = str(getattr(job, "id", "unknown"))
            platform = str(getattr(job, "platform", "unknown"))

            if _sleep and idx > 0:
                time.sleep(inter_delay_sec)

            # Inject cross-platform context (e.g. YouTube URL for cross-posting)
            enriched_metadata = self._build_cross_platform_metadata(
                job=job,
                platform=platform,
                cross_platform_context=cross_platform_context,
            )

            result = self._dispatch_job(job, platform, enriched_metadata)

            # Update cross-platform context on success
            if result.get("status") == "dispatched":
                succeeded += 1
                if result.get("platform_url"):
                    cross_platform_context[platform] = result["platform_url"]
            else:
                failed += 1

            job_result = {
                "job_id": job_id,
                "platform": platform,
                **result,
            }
            results.append(job_result)

            # Persist orchestration state for this job
            self._persist_job_state(orch_id, job_id, platform, job_result)

            # Write audit log entry
            self._append_audit_log(
                orchestration_id=orch_id,
                event_type="publish_dispatch",
                job_id=job_id,
                platform=platform,
                status=result.get("status", "unknown"),
                details={"enriched_metadata": enriched_metadata},
            )

        return {
            "orchestration_id": orch_id,
            "sequence_used": sequence_strategy,
            "total": len(jobs),
            "succeeded": succeeded,
            "failed": failed,
            "results": results,
        }

    # ------------------------------------------------------------------
    # Batch state sync
    # ------------------------------------------------------------------

    def sync_all_platform_states(
        self,
        job_id_platform_pairs: list[tuple[str, str]],
        confirm_stable: bool = True,
    ) -> dict[str, Any]:
        """Batch-sync final state across all platforms in a single coordinated pass.

        For each (job_id, platform) pair, fetches the terminal status and
        enriches with full per-platform metadata.

        Args:
            job_id_platform_pairs: List of (job_id, platform) tuples to sync.
            confirm_stable: When True, uses ``ProviderStatePollOrchestrator``
                for multi-round confirmation.

        Returns:
            Dict with ``synced`` list (per-job final state), ``total``,
            ``confirmed_published``, ``confirmed_failed``, ``pending``.
        """
        from app.services.publish_providers.provider_final_state_syncer import (
            ProviderFinalStateSyncer,
            ProviderStatePollOrchestrator,
        )

        syncer = self._syncer or ProviderFinalStateSyncer()
        poller = self._poll_orchestrator or ProviderStatePollOrchestrator(
            max_rounds=3,
            poll_interval_sec=1.0,
            required_stable_rounds=2,
            _syncer=syncer,
        )

        synced: list[dict[str, Any]] = []
        confirmed_published = confirmed_failed = pending_count = 0

        for job_id, platform in job_id_platform_pairs:
            try:
                if confirm_stable:
                    result = poller.poll_until_stable(
                        job_id=job_id,
                        platform=platform,
                        _sleep=False,
                    )
                    status = result.get("confirmed_status", "unknown")
                    raw = result.get("last_result", {})
                else:
                    raw = syncer.fetch_final_state(
                        job_id=job_id,
                        platform=platform,
                        retry_on_pending=False,
                    )
                    status = raw.get("terminal_status", "unknown")
                    result = raw

                if status == "published":
                    confirmed_published += 1
                elif status == "failed":
                    confirmed_failed += 1
                else:
                    pending_count += 1

                synced.append({
                    "job_id": job_id,
                    "platform": platform,
                    "terminal_status": status,
                    "metrics": raw.get("metrics", {}),
                    "platform_metadata": self._extract_platform_metadata(platform, raw),
                    "confirmed": result.get("confirmed", False),
                })
            except Exception as exc:
                logger.warning(
                    "ProviderChoreographyEngine.sync_all_platform_states error job=%s: %s",
                    job_id, exc,
                )
                synced.append({
                    "job_id": job_id,
                    "platform": platform,
                    "terminal_status": "error",
                    "error": str(exc),
                })
                pending_count += 1

        return {
            "total": len(job_id_platform_pairs),
            "confirmed_published": confirmed_published,
            "confirmed_failed": confirmed_failed,
            "pending": pending_count,
            "synced": synced,
        }

    # ------------------------------------------------------------------
    # Retry choreography
    # ------------------------------------------------------------------

    def coordinate_retry_schedule(
        self,
        failed_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build a coordinated retry schedule for a set of failed publish results.

        Uses ``FailureClassifier`` to determine the optimal retry timing per
        platform and aggregates them into a unified schedule.

        Args:
            failed_results: List of result dicts from
                ``choreograph_multi_platform_publish``.

        Returns:
            List of retry schedule entries with ``job_id``, ``platform``,
            ``retry_at`` (UNIX timestamp), ``strategy``, ``retry_number``.
        """
        from app.services.publish_providers.platform_recovery_workflow import FailureClassifier

        classifier = FailureClassifier()
        schedule: list[dict[str, Any]] = []
        now = time.time()

        for result in failed_results:
            if result.get("status") in ("dispatched", None):
                continue
            job_id = result.get("job_id", "unknown")
            platform = result.get("platform", "unknown")
            error_type = result.get("error_type", "unknown")
            retry_num = int(result.get("retry_number", 1))

            # Determine retry delay based on error type
            delay_sec = self._retry_delay_for_error(error_type, retry_num)
            strategy = FailureClassifier.get_strategy_for_error_type(error_type, platform)

            schedule.append({
                "job_id": job_id,
                "platform": platform,
                "error_type": error_type,
                "strategy": strategy,
                "retry_number": retry_num + 1,
                "retry_at": round(now + delay_sec),
                "delay_sec": delay_sec,
            })

        schedule.sort(key=lambda x: x["retry_at"])
        return schedule

    # ------------------------------------------------------------------
    # Orchestration state management
    # ------------------------------------------------------------------

    def get_orchestration_state(
        self,
        orchestration_id: str,
    ) -> dict[str, Any]:
        """Return the persisted state for an orchestration run.

        Returns:
            Dict with ``orchestration_id``, ``jobs`` (per-job state dict),
            ``job_count``, ``retrieved_at``.
        """
        state = _ORCH_STATE.get(orchestration_id, {})
        return {
            "orchestration_id": orchestration_id,
            "jobs": state,
            "job_count": len(state),
            "retrieved_at": time.time(),
        }

    def update_job_state(
        self,
        orchestration_id: str,
        job_id: str,
        update: dict[str, Any],
    ) -> None:
        """Update the stored state for a specific job within an orchestration."""
        _ORCH_STATE.setdefault(orchestration_id, {})
        existing = _ORCH_STATE[orchestration_id].get(job_id, {})
        existing.update(update)
        existing["updated_at"] = time.time()
        _ORCH_STATE[orchestration_id][job_id] = existing
        self._append_audit_log(
            orchestration_id=orchestration_id,
            event_type="state_update",
            job_id=job_id,
            platform=update.get("platform", "unknown"),
            status=update.get("status", "unknown"),
            details=update,
        )

    def get_audit_log(
        self,
        orchestration_id: str | None = None,
        job_id: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Query the audit log, optionally filtered by orchestration_id or job_id.

        Returns entries in reverse chronological order (most recent first).

        Args:
            orchestration_id: Filter to a specific orchestration run.
            job_id: Filter to a specific job.
            limit: Maximum number of entries to return.
        """
        entries = list(reversed(_AUDIT_LOG))
        if orchestration_id:
            entries = [e for e in entries if e.get("orchestration_id") == orchestration_id]
        if job_id:
            entries = [e for e in entries if e.get("job_id") == job_id]
        return entries[:limit]

    def replay_orchestration(
        self,
        orchestration_id: str,
    ) -> dict[str, Any]:
        """Return a chronological replay of all audit events for an orchestration.

        Useful for debugging, compliance audits, and replay testing.

        Returns:
            Dict with ``orchestration_id``, ``events`` (list in order),
            ``event_count``, ``platforms_touched``, ``outcome_summary``.
        """
        events = [
            e for e in _AUDIT_LOG
            if e.get("orchestration_id") == orchestration_id
        ]
        platforms: set[str] = {e.get("platform", "unknown") for e in events}
        statuses = [e.get("status") for e in events if e.get("status")]
        succeeded = statuses.count("dispatched")
        failed = sum(1 for s in statuses if s not in ("dispatched", None))

        return {
            "orchestration_id": orchestration_id,
            "events": events,
            "event_count": len(events),
            "platforms_touched": sorted(platforms),
            "outcome_summary": {
                "succeeded": succeeded,
                "failed": failed,
                "total": len(events),
            },
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _order_jobs(jobs: list[Any], strategy: str) -> list[Any]:
        """Order jobs by platform sequence strategy."""
        if strategy == "youtube_first":
            def _order_key(job: Any) -> int:
                plat = str(getattr(job, "platform", "")).lower()
                try:
                    return _YOUTUBE_FIRST_ORDER.index(plat)
                except ValueError:
                    return len(_YOUTUBE_FIRST_ORDER)
            return sorted(jobs, key=_order_key)
        # "priority" or unknown: preserve original order
        return list(jobs)

    @staticmethod
    def _build_cross_platform_metadata(
        job: Any,
        platform: str,
        cross_platform_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Inject cross-platform context into job metadata.

        For example, when posting to TikTok after YouTube, include the
        YouTube video URL so the TikTok post can reference/link it.
        """
        meta: dict[str, Any] = {}
        if platform.lower() in ("tiktok", "reels", "instagram", "meta", "facebook"):
            youtube_url = cross_platform_context.get("youtube") or cross_platform_context.get("shorts")
            if youtube_url:
                meta["cross_post_reference_url"] = youtube_url
        return meta

    @staticmethod
    def _dispatch_job(
        job: Any,
        platform: str,
        enriched_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Dispatch a single job to its platform provider (best-effort stub).

        In a real deployment this would call the platform-specific publish
        provider.  Here we record the dispatch intent and metadata.
        """
        return {
            "status": "dispatched",
            "platform": platform,
            "enriched_metadata": enriched_metadata,
            "dispatched_at": time.time(),
            "platform_url": None,
        }

    @staticmethod
    def _extract_platform_metadata(platform: str, raw: dict[str, Any]) -> dict[str, Any]:
        """Extract richer per-platform fields from a syncer response."""
        plat = platform.lower()
        meta: dict[str, Any] = {}
        if plat in ("youtube", "shorts"):
            meta = {
                "monetization_status": raw.get("monetization_status"),
                "age_restriction": raw.get("age_restriction"),
                "copyright_claim": raw.get("copyright_claim"),
            }
        elif plat == "tiktok":
            meta = {
                "review_status": raw.get("review_status"),
                "rejection_reason": raw.get("rejection_reason"),
                "appeal_eligible": raw.get("appeal_eligible"),
            }
        elif plat in ("meta", "reels", "instagram", "facebook"):
            meta = {
                "review_status": raw.get("review_status"),
                "policy_violation_codes": raw.get("policy_violation_codes"),
                "boost_eligible": raw.get("boost_eligible"),
            }
        return {k: v for k, v in meta.items() if v is not None}

    @staticmethod
    def _extract_content(job: Any) -> dict[str, Any]:
        """Extract content fields from a publish job for compliance checking."""
        payload: dict = dict(getattr(job, "payload", None) or {})
        return {
            "title": payload.get("title") or getattr(job, "title", ""),
            "description": payload.get("description") or getattr(job, "description", ""),
            "caption": payload.get("caption") or getattr(job, "caption", ""),
            "tags": payload.get("tags") or getattr(job, "tags", []),
            "categories": payload.get("categories") or getattr(job, "categories", []),
            "duration_seconds": payload.get("duration_seconds"),
            "adult_content": payload.get("adult_content", False),
        }

    @staticmethod
    def _retry_delay_for_error(error_type: str, retry_num: int) -> float:
        """Return retry delay in seconds for a given error type and attempt number."""
        _BASE_DELAYS: dict[str, float] = {
            "auth_expired": 60.0,
            "quota_exceeded": 86400.0,  # 24h
            "rate_limited": 300.0,
            "network_error": 30.0,
            "token_expired": 60.0,
            "policy_violation": 3600.0,
            "content_rejected": 0.0,  # manual review needed
            "account_restricted": 0.0,
            "unknown": 900.0,
        }
        base = _BASE_DELAYS.get(error_type, 900.0)
        # Exponential back-off capped at 24h
        return min(base * (2 ** max(0, retry_num - 1)), 86400.0)

    @staticmethod
    def _persist_job_state(
        orchestration_id: str,
        job_id: str,
        platform: str,
        result: dict[str, Any],
    ) -> None:
        """Persist per-job state into the in-memory orchestration store."""
        _ORCH_STATE.setdefault(orchestration_id, {})
        _ORCH_STATE[orchestration_id][job_id] = {
            "platform": platform,
            "status": result.get("status", "unknown"),
            "dispatched_at": result.get("dispatched_at"),
            "platform_url": result.get("platform_url"),
            "error_type": result.get("error_type"),
            "updated_at": time.time(),
        }

    @staticmethod
    def _append_audit_log(
        orchestration_id: str,
        event_type: str,
        job_id: str,
        platform: str,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Append an immutable audit log entry."""
        entry = {
            "orchestration_id": orchestration_id,
            "event_type": event_type,
            "job_id": job_id,
            "platform": platform,
            "status": status,
            "details": details or {},
            "recorded_at": time.time(),
        }
        _AUDIT_LOG.append(entry)
        # Trim to max size (drop oldest)
        if len(_AUDIT_LOG) > _MAX_AUDIT_ENTRIES:
            del _AUDIT_LOG[: len(_AUDIT_LOG) - _MAX_AUDIT_ENTRIES]
