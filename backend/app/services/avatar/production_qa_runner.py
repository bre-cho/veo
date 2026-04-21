"""ProductionQARunner — always-on bulk quality assurance for render outputs.

Completes the avatar fidelity stack by providing an always-on production
extractor path that processes *all* pending render jobs through:

1. ``render_qa_hook.execute_qa_for_job()`` — per-job identity + quality gate.
2. ``VideoQualityAnalyzer.analyze_video()`` — deep multi-frame temporal QA.
3. ``MultiEpisodeIdentityGovernor`` — cross-episode governance update.

The runner is designed to be called from:
- A Celery beat task (periodic)
- An API endpoint (on-demand)
- Triggered by the render FSM post-render state

Usage::

    runner = ProductionQARunner(db=db)
    summary = runner.run_pending_jobs(limit=50)
    # summary["processed"] → int
    # summary["passed"]    → int
    # summary["failed"]    → int
    # summary["skipped"]   → int
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Minimum quality score to update the canonical reference after full video QA
_VIDEO_QA_CANONICAL_UPDATE_THRESHOLD = 0.75
# Status values for jobs that need QA
_PENDING_STATUSES = frozenset({"identity_review", "completed", "published"})
# Maximum full video QA failures before quarantining an avatar
_MAX_VIDEO_QA_FAILURES = 5

# In-memory failure tracker: {avatar_id → failure_count}
_VIDEO_QA_FAIL_COUNTS: dict[str, int] = {}


class ProductionQARunner:
    """Always-on production QA runner for render outputs.

    Parameters
    ----------
    db:
        SQLAlchemy session for querying RenderJob/PublishJob tables.
    identity_governor:
        Optional ``MultiEpisodeIdentityGovernor`` for cross-episode QA.
    """

    def __init__(
        self,
        db: Any | None = None,
        identity_governor: Any | None = None,
    ) -> None:
        self._db = db
        self._governor = identity_governor

    # ------------------------------------------------------------------
    # Batch processing
    # ------------------------------------------------------------------

    def run_pending_jobs(
        self,
        limit: int = 50,
        run_video_qa: bool = True,
    ) -> dict[str, Any]:
        """Process all render jobs that need QA.

        Iterates over render jobs in ``identity_review`` / ``completed``
        state, runs QA, and marks them ``qa_passed`` or ``qa_failed``.

        Args:
            limit: Maximum jobs to process in a single run.
            run_video_qa: When True, also run full VideoQualityAnalyzer on
                each job (more expensive but more thorough).

        Returns:
            Dict with ``processed``, ``passed``, ``failed``, ``skipped``,
            ``quarantined_avatars``.
        """
        if self._db is None:
            return {"error": "db_unavailable", "processed": 0}

        jobs = self._fetch_pending_jobs(limit)
        processed = passed = failed = skipped = 0
        quarantined: list[str] = []

        for job in jobs:
            try:
                result = self.run_full_qa_for_job(job, run_video_qa=run_video_qa)
                status = result.get("status")
                if status == "passed":
                    passed += 1
                elif status == "failed":
                    failed += 1
                    avatar_id = self._extract_avatar_id(job)
                    if avatar_id and self._is_quarantine_threshold_reached(avatar_id):
                        quarantined.append(avatar_id)
                        logger.warning(
                            "ProductionQARunner: avatar=%s quarantined after %d consecutive failures",
                            avatar_id,
                            _MAX_VIDEO_QA_FAILURES,
                        )
                else:
                    skipped += 1
                processed += 1
            except Exception as exc:
                logger.warning("ProductionQARunner: job processing error: %s", exc)
                skipped += 1

        logger.info(
            "ProductionQARunner: processed=%d passed=%d failed=%d skipped=%d",
            processed,
            passed,
            failed,
            skipped,
        )
        return {
            "processed": processed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "quarantined_avatars": list(set(quarantined)),
        }

    def run_full_qa_for_job(
        self,
        job: Any,
        run_video_qa: bool = True,
    ) -> dict[str, Any]:
        """Run full QA pipeline for a single render job.

        Pipeline:
        1. ``render_qa_hook.execute_qa_for_job()`` — identity + basic quality.
        2. ``VideoQualityAnalyzer.analyze_video()`` — temporal multi-frame QA.
        3. Update ``MultiEpisodeIdentityGovernor`` with the episode result.

        Returns:
            Dict with ``job_id``, ``status`` ("passed"|"failed"|"skipped"),
            ``identity_qa``, ``video_qa``, ``governance_update``.
        """
        job_id = str(getattr(job, "id", "unknown"))
        payload: dict = dict(getattr(job, "payload", None) or {})
        render_url: str | None = str(payload.get("output_url") or payload.get("render_url") or "").strip() or None

        if not render_url:
            return {"job_id": job_id, "status": "skipped", "reason": "no_render_url"}

        avatar_id = self._extract_avatar_id(job)

        # --- Step 1: Identity QA via render_qa_hook ---
        identity_qa: dict[str, Any] = {}
        try:
            from app.services.avatar.render_qa_hook import execute_qa_for_job  # type: ignore[import]
            identity_qa = execute_qa_for_job(job, db=self._db) or {}
        except Exception as exc:
            logger.debug("ProductionQARunner: identity QA failed job=%s: %s", job_id, exc)
            identity_qa = {"passed": False, "error": str(exc)}

        # --- Step 2: Full video QA ---
        video_qa: dict[str, Any] = {}
        if run_video_qa and render_url:
            video_qa = self._run_video_qa(render_url)

        # --- Overall pass/fail ---
        identity_passed = bool(identity_qa.get("passed", True))
        video_passed = (
            video_qa.get("composite_quality_score", 1.0) >= _VIDEO_QA_CANONICAL_UPDATE_THRESHOLD
            if video_qa
            else True
        )
        overall_passed = identity_passed and video_passed

        if overall_passed:
            _VIDEO_QA_FAIL_COUNTS.pop(avatar_id or "", None)
        elif avatar_id:
            _VIDEO_QA_FAIL_COUNTS[avatar_id] = _VIDEO_QA_FAIL_COUNTS.get(avatar_id, 0) + 1

        # --- Step 3: Update MultiEpisodeIdentityGovernor when possible ---
        governance_update: dict[str, Any] = {}
        if avatar_id and overall_passed:
            governance_update = self._update_episode_governance(
                avatar_id=avatar_id,
                job=job,
                identity_qa=identity_qa,
                video_qa=video_qa,
            )

        return {
            "job_id": job_id,
            "render_url": render_url,
            "avatar_id": avatar_id,
            "status": "passed" if overall_passed else "failed",
            "identity_qa": identity_qa,
            "video_qa": video_qa,
            "governance_update": governance_update,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_pending_jobs(self, limit: int) -> list[Any]:
        """Fetch render jobs that need QA from the DB."""
        try:
            from app.models.render_job import RenderJob  # type: ignore[import]

            return (
                self._db.query(RenderJob)
                .filter(RenderJob.status.in_(list(_PENDING_STATUSES)))
                .order_by(RenderJob.updated_at.desc())
                .limit(limit)
                .all()
            )
        except Exception as exc:
            logger.warning("ProductionQARunner._fetch_pending_jobs failed: %s", exc)
            return []

    @staticmethod
    def _run_video_qa(render_url: str) -> dict[str, Any]:
        """Run VideoQualityAnalyzer on a render URL."""
        try:
            from app.services.avatar.render_quality_gate import VideoQualityAnalyzer
            analyzer = VideoQualityAnalyzer()
            return analyzer.analyze_video(render_url)
        except Exception as exc:
            logger.debug("ProductionQARunner._run_video_qa failed url=%s: %s", render_url, exc)
            return {}

    @staticmethod
    def _extract_avatar_id(job: Any) -> str | None:
        """Extract avatar_id from a render job."""
        payload: dict = dict(getattr(job, "payload", None) or {})
        avatar_id = payload.get("avatar_id") or getattr(job, "avatar_id", None)
        return str(avatar_id) if avatar_id else None

    def _update_episode_governance(
        self,
        avatar_id: str,
        job: Any,
        identity_qa: dict[str, Any],
        video_qa: dict[str, Any],
    ) -> dict[str, Any]:
        """Update MultiEpisodeIdentityGovernor with QA results."""
        try:
            from app.services.avatar.multi_episode_identity_governor import (
                MultiEpisodeIdentityGovernor,
            )

            governor = self._governor or MultiEpisodeIdentityGovernor(db=self._db)
            payload: dict = dict(getattr(job, "payload", None) or {})
            series_id = str(payload.get("series_id") or "default")
            episode_number = int(payload.get("episode_number") or 1)
            embedding = list(identity_qa.get("embedding") or [])
            quality_score = float(
                video_qa.get("composite_quality_score")
                or identity_qa.get("similarity_score", 0.5)
            )
            render_url = str(payload.get("output_url") or payload.get("render_url") or "")

            result = governor.record_episode_identity(
                series_id=series_id,
                avatar_id=avatar_id,
                episode_number=episode_number,
                embedding=embedding,
                render_url=render_url or None,
                quality_score=quality_score,
            )
            # Persist governance state to DB
            governor.persist_to_db(series_id=series_id, avatar_id=avatar_id)
            return result
        except Exception as exc:
            logger.debug("ProductionQARunner._update_episode_governance failed: %s", exc)
            return {}

    @staticmethod
    def _is_quarantine_threshold_reached(avatar_id: str) -> bool:
        return _VIDEO_QA_FAIL_COUNTS.get(avatar_id, 0) >= _MAX_VIDEO_QA_FAILURES
