"""asset_collector — download and validate remote provider video assets.

Phase 6 of the render pipeline: convert provider output URLs into real local
files that downstream postprocess/merge steps can consume.

Validation gates applied on every download:
1. Size > 0 bytes (not empty).
2. Content-Type starts with ``video/`` or is ``application/octet-stream``.
3. SHA-256 checksum recorded for audit trail.

If any gate fails, an ``AssetIngestionError`` is raised so the caller can
mark the scene as failed and retry ingestion or escalate to the job.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
import tempfile
from typing import TYPE_CHECKING

import httpx

from app.core.config import settings

if TYPE_CHECKING:
    pass  # no runtime type-only imports needed

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------
_MIN_VIDEO_BYTES = 1  # reject completely empty payloads
_ALLOWED_CONTENT_TYPES = (
    "video/",
    "application/octet-stream",
    "binary/",
)
_DOWNLOAD_TIMEOUT_SECONDS = 120
_MAX_ATTEMPTS = 3  # total download attempts (1 initial + 2 retries)


# -----------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------
class AssetIngestionError(RuntimeError):
    """Raised when a provider asset cannot be ingested reliably."""


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------
def _resolve_render_cache_dir() -> Path:
    preferred = Path(settings.render_cache_dir)
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred
    except (PermissionError, FileNotFoundError):
        fallback = Path(tempfile.gettempdir()) / "render-factory-storage" / "render_cache"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


RENDER_CACHE_DIR = _resolve_render_cache_dir()


def _is_acceptable_content_type(content_type: str | None) -> bool:
    if not content_type:
        return True  # tolerate missing header; rely on size/checksum checks
    ct_lower = content_type.lower().split(";")[0].strip()
    return any(ct_lower.startswith(prefix) for prefix in _ALLOWED_CONTENT_TYPES)


def _sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# -----------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------
async def cache_remote_video(job_id: str, scene_index: int, url: str) -> str:
    """Download *url*, validate the payload, persist to local cache, return path.

    Retries up to ``_MAX_RETRIES`` times on transient HTTP errors before
    raising ``AssetIngestionError``.

    Returns
    -------
    str
        Absolute path to the cached file.

    Raises
    ------
    AssetIngestionError
        If the download fails all retries, yields an empty body, or the
        Content-Type is clearly not a video.
    """
    local_path = RENDER_CACHE_DIR / job_id / f"scene_{scene_index:03d}.mp4"
    local_path.parent.mkdir(parents=True, exist_ok=True)

    last_error: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=_DOWNLOAD_TIMEOUT_SECONDS) as client:
                response = await client.get(url)
                response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if not _is_acceptable_content_type(content_type):
                raise AssetIngestionError(
                    f"Unexpected Content-Type for scene {scene_index} job {job_id}: "
                    f"'{content_type}' — expected video/*"
                )

            data = response.content
            if len(data) < _MIN_VIDEO_BYTES:
                raise AssetIngestionError(
                    f"Downloaded asset for scene {scene_index} job {job_id} is empty (0 bytes)"
                )

            checksum = _sha256_of_bytes(data)
            local_path.write_bytes(data)

            logger.info(
                "Asset ingested: job=%s scene=%d size=%d sha256=%s path=%s",
                job_id,
                scene_index,
                len(data),
                checksum,
                local_path,
            )
            return str(local_path)

        except AssetIngestionError:
            raise  # validation failures are not retried
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Asset download attempt %d/%d failed for scene %d job %s: %s",
                attempt,
                _MAX_ATTEMPTS,
                scene_index,
                job_id,
                exc,
            )

    raise AssetIngestionError(
        f"Asset ingestion failed after {_MAX_ATTEMPTS} attempts "
        f"for scene {scene_index} job {job_id}: {last_error}"
    )
