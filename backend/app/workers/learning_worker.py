"""learning_worker — background worker that runs adaptive learning on recent publish outcomes."""
from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 120
_PUBLISHED_JOB_WINDOW_MINUTES = 60


def run_learning_loop(db_session_factory: Any) -> None:
    """Continuously poll for recently published jobs and run adaptive
    learning via :class:`AdaptiveLearningEngine`.

    Parameters
    ----------
    db_session_factory:
        Callable that returns a new SQLAlchemy ``Session`` when called.
    """
    from app.services.avatar.learning_engine import AdaptiveLearningEngine

    learning_engine = AdaptiveLearningEngine()
    logger.info("learning_worker: starting loop (interval=%ss)", _POLL_INTERVAL_SECONDS)

    while True:
        try:
            db = db_session_factory()
            try:
                _process_published_jobs(db, learning_engine)
            finally:
                db.close()
        except Exception as exc:
            logger.error("learning_worker: unhandled error: %s", exc, exc_info=True)

        time.sleep(_POLL_INTERVAL_SECONDS)


def _process_published_jobs(db: Any, learning_engine: Any) -> None:
    from datetime import datetime, timedelta, timezone

    from app.models.publish_job import PublishJob

    cutoff = (
        datetime.now(timezone.utc).replace(tzinfo=None)
        - timedelta(minutes=_PUBLISHED_JOB_WINDOW_MINUTES)
    )

    published_jobs = (
        db.query(PublishJob)
        .filter(
            PublishJob.status == "published",
            PublishJob.published_at >= cutoff,
            PublishJob.signal_status == "pending",
        )
        .limit(50)
        .all()
    )

    for job in published_jobs:
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
                "topic_signature": metadata.get("topic_signature"),
                "template_family": metadata.get("selected_template_family"),
                "platform": job.platform,
            }

            result = learning_engine.learn(
                db=db,
                avatar_id=avatar_id,
                context=context,
                metrics=metrics,
            )

            logger.debug(
                "learning_worker: learned avatar=%s reward=%.3f job=%s",
                avatar_id,
                result.reward,
                job.id,
            )
        except Exception as exc:
            logger.warning(
                "learning_worker: failed to process job=%s: %s", job.id, exc
            )
