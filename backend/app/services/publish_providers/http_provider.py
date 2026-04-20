from __future__ import annotations

import json as _json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from app.models.publish_job import PublishJob
from app.services.publish_providers.base import PublishProviderBase

PUBLISH_MODE_REAL = "REAL"

# Retriable HTTP status codes: server-side errors only (5xx).
# Client errors (4xx) indicate a bad request and should not be retried.
_RETRIABLE_STATUS_CODES = frozenset(range(500, 600))


class ConfigurationError(Exception):
    """Raised when a required environment variable is missing or invalid."""


class HttpPublishProvider(PublishProviderBase):
    """Generic HTTP publish provider.

    Reads target URL and auth token from environment variables:
      - ``PUBLISH_PROVIDER_URL``  (required when PUBLISH_MODE=REAL)
      - ``PUBLISH_PROVIDER_TOKEN`` (optional – sent as Bearer token)

    Retry / backoff settings are taken from ``app.core.config.settings``:
      - ``provider_max_retries``        (default 2, so up to 3 total attempts)
      - ``provider_retry_base_seconds`` (default 2 s, doubles each attempt)

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

    def execute(self, job: PublishJob) -> dict[str, Any]:
        """POST the job payload to the configured provider URL.

        Retries on transient 5xx and network errors with exponential back-off.
        Non-retriable 4xx errors are raised immediately.
        """
        from app.core.config import settings

        max_retries: int = settings.provider_max_retries
        backoff_base: float = float(settings.provider_retry_base_seconds)

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

        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                raw = self._do_request(body, headers)
                return {
                    "ok": bool(raw.get("ok", True)),
                    "mode": PUBLISH_MODE_REAL,
                    "provider_publish_id": (
                        raw.get("provider_publish_id") or raw.get("id") or job.id
                    ),
                    "raw": raw,
                }
            except urllib.error.HTTPError as exc:
                if exc.code not in _RETRIABLE_STATUS_CODES:
                    # 4xx or other non-retriable status – propagate immediately
                    raise
                last_exc = exc
            except (urllib.error.URLError, OSError) as exc:
                last_exc = exc

            if attempt < max_retries:
                self._sleep(backoff_base * (2 ** attempt))

        if last_exc is not None:
            raise last_exc
        # This line is unreachable in practice but guards against unforeseen control flow.
        raise RuntimeError("HttpPublishProvider.execute() exhausted retries without capturing an exception")

    def _do_request(self, body: bytes, headers: dict[str, str]) -> dict[str, Any]:
        """Execute the HTTP request and return the decoded JSON body."""
        req = urllib.request.Request(
            self._url, data=body, headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            return _json.loads(resp.read())

    @staticmethod
    def _sleep(seconds: float) -> None:  # pragma: no cover
        time.sleep(seconds)
