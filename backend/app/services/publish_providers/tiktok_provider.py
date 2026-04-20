"""TikTok-specific publish provider.

Formats the job payload for the TikTok Content Posting API and delegates to
the HTTP layer.  Auth uses a user-access-token supplied via
``TIKTOK_ACCESS_TOKEN`` (or ``PUBLISH_PROVIDER_TOKEN``).

Upload URL is read from ``TIKTOK_UPLOAD_URL`` or ``PUBLISH_PROVIDER_URL``.
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
PLATFORM = "tiktok"

_RETRIABLE_STATUS_CODES = frozenset(range(500, 600))

# Supported privacy levels by the TikTok Content Posting API
_PRIVACY_LEVEL_MAP = {
    "public": "PUBLIC_TO_EVERYONE",
    "friends": "MUTUAL_FOLLOW_FRIENDS",
    "private": "SELF_ONLY",
}


class ConfigurationError(Exception):
    """Raised when a required environment variable is missing."""


class TikTokPublishProvider(PublishProviderBase):
    """TikTok Content Posting API adapter.

    Reads configuration from:
      - ``TIKTOK_UPLOAD_URL``    URL of the TikTok upload proxy / middleware
      - ``TIKTOK_ACCESS_TOKEN``  User access token
      - ``PUBLISH_PROVIDER_URL`` / ``PUBLISH_PROVIDER_TOKEN`` as fallbacks
    """

    def __init__(self) -> None:
        self._url = (
            os.environ.get("TIKTOK_UPLOAD_URL", "").strip()
            or os.environ.get("PUBLISH_PROVIDER_URL", "").strip()
        )
        self._token = (
            os.environ.get("TIKTOK_ACCESS_TOKEN", "").strip()
            or os.environ.get("PUBLISH_PROVIDER_TOKEN", "").strip()
        )
        if not self._url:
            raise ConfigurationError(
                "TIKTOK_UPLOAD_URL (or PUBLISH_PROVIDER_URL) is required when "
                "publishing to TikTok.  Set it to your upload proxy endpoint."
            )

    def execute(self, job: PublishJob) -> dict[str, Any]:
        """POST a TikTok-shaped payload and return the normalised response."""
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
        raise RuntimeError("TikTokPublishProvider.execute() exhausted retries without exception")

    @staticmethod
    def _build_payload(job: PublishJob) -> dict[str, Any]:
        """Map the generic job payload to TikTok Content Posting API conventions."""
        payload: dict[str, Any] = job.payload or {}
        metadata: dict[str, Any] = payload.get("metadata") or {}
        raw_privacy = str(metadata.get("privacy_status") or "public").lower()
        privacy_level = _PRIVACY_LEVEL_MAP.get(raw_privacy, "PUBLIC_TO_EVERYONE")
        return {
            "job_id": job.id,
            "platform": PLATFORM,
            "publish_mode": job.publish_mode,
            # TikTok Content Posting API fields
            "post_info": {
                "title": str(payload.get("title_angle") or metadata.get("channel_name") or ""),
                "privacy_level": privacy_level,
                "disable_duet": bool(metadata.get("disable_duet", False)),
                "disable_comment": bool(metadata.get("disable_comment", False)),
                "disable_stitch": bool(metadata.get("disable_stitch", False)),
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": str(metadata.get("video_url") or ""),
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
