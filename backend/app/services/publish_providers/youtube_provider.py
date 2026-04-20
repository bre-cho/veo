"""YouTube-specific publish provider.

Formats the job payload according to YouTube Data API v3 video insert
conventions and delegates to the HTTP layer for the actual POST.  Auth is
handled via a service-account access token supplied through the
``YOUTUBE_API_TOKEN`` environment variable (or falls back to
``PUBLISH_PROVIDER_TOKEN``).

The provider expects a configured ``YOUTUBE_UPLOAD_URL`` or falls back to the
generic ``PUBLISH_PROVIDER_URL``.
"""
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
PLATFORM = "youtube"

_RETRIABLE_STATUS_CODES = frozenset(range(500, 600))

_DEFAULT_CATEGORY_ID = "22"  # People & Blogs


class ConfigurationError(Exception):
    """Raised when a required environment variable is missing."""


class YouTubePublishProvider(PublishProviderBase):
    """YouTube Data API v3 publish adapter.

    Reads configuration from environment variables:
      - ``YOUTUBE_UPLOAD_URL``   URL of the YouTube upload proxy / middleware
      - ``YOUTUBE_API_TOKEN``    OAuth2 / service-account access token
      - ``PUBLISH_PROVIDER_URL`` Fallback URL when YOUTUBE_UPLOAD_URL is unset
      - ``PUBLISH_PROVIDER_TOKEN`` Fallback token

    Posts a YouTube-shaped JSON body and expects a response that includes
    ``{"ok": bool, "provider_publish_id": str}``.
    """

    def __init__(self) -> None:
        self._url = (
            os.environ.get("YOUTUBE_UPLOAD_URL", "").strip()
            or os.environ.get("PUBLISH_PROVIDER_URL", "").strip()
        )
        self._token = (
            os.environ.get("YOUTUBE_API_TOKEN", "").strip()
            or os.environ.get("PUBLISH_PROVIDER_TOKEN", "").strip()
        )
        if not self._url:
            raise ConfigurationError(
                "YOUTUBE_UPLOAD_URL (or PUBLISH_PROVIDER_URL) is required when "
                "publishing to YouTube.  Set it to your upload proxy endpoint."
            )

    def execute(self, job: PublishJob) -> dict[str, Any]:
        """POST a YouTube-shaped payload and return the normalised response."""
        from app.core.config import settings

        max_retries: int = settings.provider_max_retries
        backoff_base: float = float(settings.provider_retry_base_seconds)

        body = _json.dumps(self._build_payload(job)).encode()
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
                    "platform": PLATFORM,
                    "provider_publish_id": raw.get("provider_publish_id") or raw.get("id") or job.id,
                    "raw": raw,
                }
            except urllib.error.HTTPError as exc:
                if exc.code not in _RETRIABLE_STATUS_CODES:
                    raise
                last_exc = exc
            except (urllib.error.URLError, OSError) as exc:
                last_exc = exc

            if attempt < max_retries:
                self._sleep(backoff_base * (2 ** attempt))

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("YouTubePublishProvider.execute() exhausted retries without exception")

    @staticmethod
    def _build_payload(job: PublishJob) -> dict[str, Any]:
        """Map the generic job payload to YouTube Data API v3 conventions."""
        payload: dict[str, Any] = job.payload or {}
        metadata: dict[str, Any] = payload.get("metadata") or {}
        return {
            "job_id": job.id,
            "platform": PLATFORM,
            "publish_mode": job.publish_mode,
            # YouTube-specific fields
            "snippet": {
                "title": str(payload.get("title_angle") or metadata.get("channel_name") or "Untitled"),
                "description": str(payload.get("content_goal") or ""),
                "categoryId": str(metadata.get("category_id") or _DEFAULT_CATEGORY_ID),
                "tags": metadata.get("tags") or [],
            },
            "status": {
                "privacyStatus": str(metadata.get("privacy_status") or "public"),
                "selfDeclaredMadeForKids": bool(metadata.get("made_for_kids", False)),
            },
            "payload": payload,
        }

    def _do_request(self, body: bytes, headers: dict[str, str]) -> dict[str, Any]:
        req = urllib.request.Request(self._url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            return _json.loads(resp.read())

    @staticmethod
    def _sleep(seconds: float) -> None:  # pragma: no cover
        time.sleep(seconds)
