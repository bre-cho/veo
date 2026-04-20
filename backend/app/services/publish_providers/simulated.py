from __future__ import annotations

from typing import Any

from app.models.publish_job import PublishJob
from app.services.publish_providers.base import PublishProviderBase

PUBLISH_MODE_SIMULATED = "SIMULATED"


class SimulatedPublishProvider(PublishProviderBase):
    """Returns a clearly-marked simulated response so QA can identify it in DB."""

    def execute(self, job: PublishJob) -> dict[str, Any]:
        return {
            "ok": True,
            "mode": PUBLISH_MODE_SIMULATED,
            "provider_publish_id": f"sim-{job.id[:8]}",
            "note": "This is a SIMULATED publish – no real provider was called.",
        }
