"""self_healing_worker — background worker that processes recent failed jobs for self-healing."""
from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 60
_FAILED_JOB_WINDOW_MINUTES = 30


def run_self_healing_loop(db_session_factory: Any) -> None:
    """Continuously poll for recently failed publish jobs and attempt
    self-healing via :class:`SelfHealingEngine`.

    Parameters
    ----------
    db_session_factory:
        Callable that returns a new SQLAlchemy ``Session`` when called.
    """
    from app.models.publish_job import PublishJob
    from app.services.avatar.self_healing_engine import SelfHealingEngine

    healing_engine = SelfHealingEngine()
    logger.info("self_healing_worker: starting loop (interval=%ss)", _POLL_INTERVAL_SECONDS)

    while True:
        try:
            db = db_session_factory()
            try:
                _process_failed_jobs(db, healing_engine)
            finally:
                db.close()
        except Exception as exc:
            logger.error("self_healing_worker: unhandled error: %s", exc, exc_info=True)

        time.sleep(_POLL_INTERVAL_SECONDS)


def _process_failed_jobs(db: Any, healing_engine: Any) -> None:
    from datetime import datetime, timedelta, timezone

    from app.models.publish_job import PublishJob

    cutoff = (
        datetime.now(timezone.utc).replace(tzinfo=None)
        - timedelta(minutes=_FAILED_JOB_WINDOW_MINUTES)
    )

    failed_jobs = (
        db.query(PublishJob)
        .filter(
            PublishJob.status == "failed",
            PublishJob.failed_at >= cutoff,
        )
        .limit(50)
        .all()
    )

    for job in failed_jobs:
        try:
            payload: dict = job.payload or {}
            metadata: dict = payload.get("metadata") or {}
            avatar_id: str | None = (
                metadata.get("avatar_id") or payload.get("avatar_id")
            )
            if not avatar_id:
                continue

            metrics: dict = metadata.get("metrics") or {}
            context: dict = {
                "project_id": payload.get("project_id") or metadata.get("project_id"),
                "platform": job.platform,
                "topic_class": metadata.get("topic_class"),
                "template_family": metadata.get("selected_template_family"),
                "topic_signature": metadata.get("topic_signature"),
                "candidate_avatar_ids": metadata.get("candidate_avatar_ids") or [],
            }

            result = healing_engine.process_feedback(
                db=db,
                avatar_id=avatar_id,
                metrics=metrics,
                context=context,
            )

            if result.status == "healed":
                logger.info(
                    "self_healing_worker: healed avatar=%s action=%s job=%s",
                    avatar_id,
                    result.action,
                    job.id,
                )
        except Exception as exc:
            logger.warning(
                "self_healing_worker: failed to process job=%s: %s", job.id, exc
            )
