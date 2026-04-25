"""Lightweight runtime configuration — quick-verify safe.

Intentionally uses only ``os.getenv``; does **not** import pydantic, sqlalchemy,
fastapi, celery, or any other heavy dependency.  This makes it safe to import
in ``verify_unified_runtime.py --mode quick`` where the goal is a sub-10-second
import-only smoke-test without any infrastructure packages installed.

All settings available here mirror the names in ``app.core.config.Settings``
so that callers can switch between the two without changing attribute access.
"""
from __future__ import annotations

import os


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# Environment / infrastructure
# ---------------------------------------------------------------------------

app_env: str = os.getenv("APP_ENV", "development")
log_level: str = os.getenv("LOG_LEVEL", "INFO")

# ---------------------------------------------------------------------------
# Public URL
# ---------------------------------------------------------------------------

public_base_url: str | None = os.getenv("PUBLIC_BASE_URL")

# ---------------------------------------------------------------------------
# Storage paths (no default fallback to /app — lightweight only)
# ---------------------------------------------------------------------------

storage_root: str = os.getenv("STORAGE_ROOT", "/app/storage")
render_output_dir: str = os.getenv("RENDER_OUTPUT_DIR", "/app/storage/render_outputs")
render_cache_dir: str = os.getenv("RENDER_CACHE_DIR", "/app/storage/render_cache")
audio_output_dir: str = os.getenv("AUDIO_OUTPUT_DIR", "/app/storage/artifacts/audio")
video_output_dir: str = os.getenv("VIDEO_OUTPUT_DIR", "/app/storage/artifacts/video")

# ---------------------------------------------------------------------------
# Production guard — fail fast on obviously wrong localhost URLs in prod
# Only triggers when APP_ENV is explicitly set to "production" in the environment.
# ---------------------------------------------------------------------------

if os.getenv("APP_ENV", "").strip().lower() == "production":
    if not public_base_url:
        raise ValueError(
            "PUBLIC_BASE_URL is required when APP_ENV=production. "
            "Set PUBLIC_BASE_URL to the real public hostname before deploying."
        )
    if "localhost" in public_base_url:
        raise ValueError(
            "PUBLIC_BASE_URL contains 'localhost' while APP_ENV=production. "
            "Set PUBLIC_BASE_URL to the real public hostname before deploying."
        )
