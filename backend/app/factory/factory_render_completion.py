from __future__ import annotations

import os
import time
from typing import Any

from sqlalchemy.orm import Session


class FactoryRenderCompletionWatcher:
    """Poll RenderJob until completed/failed/timeout."""

    TERMINAL_SUCCESS = {"succeeded", "completed", "success"}
    TERMINAL_FAILED = {"failed", "error", "cancelled", "blocked", "canceled"}

    def __init__(
        self,
        db: Session,
        timeout_seconds: int | None = None,
        poll_interval: float = 1.0,
    ) -> None:
        self.db = db
        self.timeout_seconds = timeout_seconds or int(
            os.getenv("FACTORY_RENDER_WAIT_TIMEOUT_SECONDS", "60")
        )
        self.poll_interval = poll_interval

    def wait(self, render_job_id: str) -> dict[str, Any]:
        from app.models.render_job import RenderJob

        deadline = time.monotonic() + self.timeout_seconds
        last_status = None
        while time.monotonic() < deadline:
            job = self.db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
            if job is None:
                return {"completed": False, "failed": True, "status": "missing", "job": None}

            last_status = getattr(job, "status", None)
            if last_status in self.TERMINAL_SUCCESS:
                return {"completed": True, "failed": False, "status": last_status, "job": job}
            if last_status in self.TERMINAL_FAILED:
                return {"completed": False, "failed": True, "status": last_status, "job": job}

            self.db.expire_all()
            time.sleep(self.poll_interval)

        job = self.db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
        return {
            "completed": False,
            "failed": False,
            "timeout": True,
            "status": last_status,
            "job": job,
        }
