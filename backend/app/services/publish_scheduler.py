from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.publish_job import PublishJob

# ---------------------------------------------------------------------------
# Publish mode configuration
# Set PUBLISH_MODE=REAL in environment to enable actual provider calls.
# Default is SIMULATED so staging never accidentally fires real publishes.
# ---------------------------------------------------------------------------
PUBLISH_MODE_SIMULATED = "SIMULATED"
PUBLISH_MODE_REAL = "REAL"

_PUBLISH_MODE: str = os.getenv("PUBLISH_MODE", PUBLISH_MODE_SIMULATED).upper()


def _is_simulated() -> bool:
    return _PUBLISH_MODE != PUBLISH_MODE_REAL


class PublishProviderBase:
    """Abstraction layer for publish providers.

    Override `execute(job)` to call a real provider.  Returns a dict with
    at minimum `{"ok": bool, ...}`.
    """

    def execute(self, job: PublishJob) -> dict[str, Any]:
        raise NotImplementedError


class SimulatedPublishProvider(PublishProviderBase):
    """Returns a clearly-marked simulated response so QA can identify it in DB."""

    def execute(self, job: PublishJob) -> dict[str, Any]:
        return {
            "ok": True,
            "mode": PUBLISH_MODE_SIMULATED,
            "provider_publish_id": f"sim-{job.id[:8]}",
            "note": "This is a SIMULATED publish – no real provider was called.",
        }


class RealPublishProvider(PublishProviderBase):
    """Placeholder for the real publish provider integration.

    Replace the body of `execute()` with actual provider SDK / HTTP call.
    """

    def execute(self, job: PublishJob) -> dict[str, Any]:  # pragma: no cover – real provider not wired yet
        raise NotImplementedError(
            "Real publish provider is not yet implemented. "
            "Set PUBLISH_MODE=SIMULATED or wire up the provider."
        )


def _get_provider() -> PublishProviderBase:
    if _is_simulated():
        return SimulatedPublishProvider()
    return RealPublishProvider()


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
            )
            jobs.append(job)
            db.add(job)
        db.commit()
        for job in jobs:
            db.refresh(job)
        return jobs

    def run_job(self, db: Session, job: PublishJob) -> PublishJob:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        provider = _get_provider()
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
