from __future__ import annotations

from typing import Any

from app.models.publish_job import PublishJob


class PublishProviderBase:
    """Abstraction layer for publish providers.

    Subclasses must implement ``execute(job)`` and return a dict with at
    minimum ``{"ok": bool, ...}``.
    """

    def execute(self, job: PublishJob) -> dict[str, Any]:
        raise NotImplementedError
