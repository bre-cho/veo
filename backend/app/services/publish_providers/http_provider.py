from __future__ import annotations

import os
from typing import Any

from app.models.publish_job import PublishJob
from app.services.publish_providers.base import PublishProviderBase

PUBLISH_MODE_REAL = "REAL"


class ConfigurationError(Exception):
    """Raised when a required environment variable is missing or invalid."""


class HttpPublishProvider(PublishProviderBase):
    """Generic HTTP publish provider.

    Reads target URL and auth token from environment variables:
      - ``PUBLISH_PROVIDER_URL``  (required when PUBLISH_MODE=REAL)
      - ``PUBLISH_PROVIDER_TOKEN`` (optional – sent as Bearer token)

    The provider POSTs the job payload to the URL and expects a JSON response
    with at minimum ``{"ok": bool, "provider_publish_id": str}``.
    """

    def __init__(self) -> None:
        self._url = os.environ.get("PUBLISH_PROVIDER_URL", "").strip()
        self._token = os.environ.get("PUBLISH_PROVIDER_TOKEN", "").strip()
        if not self._url:
            raise ConfigurationError(
                "PUBLISH_PROVIDER_URL is required when PUBLISH_MODE=REAL. "
                "Set it to the provider endpoint URL or switch to PUBLISH_MODE=SIMULATED."
            )

    def execute(self, job: PublishJob) -> dict[str, Any]:  # pragma: no cover – requires live endpoint
        """POST the job payload to the configured provider URL."""
        import urllib.request
        import json as _json

        body = _json.dumps(
            {
                "job_id": job.id,
                "platform": job.platform,
                "publish_mode": job.publish_mode,
                "payload": job.payload,
            }
        ).encode()

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        req = urllib.request.Request(self._url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            raw: dict[str, Any] = _json.loads(resp.read())

        return {
            "ok": bool(raw.get("ok", True)),
            "mode": PUBLISH_MODE_REAL,
            "provider_publish_id": raw.get("provider_publish_id") or raw.get("id") or job.id,
            "raw": raw,
        }
