from __future__ import annotations

import json
from typing import Any

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.control_plane import get_or_create_worker_override, resolve_effective_provider
from app.schemas.provider_common import NormalizedSubmitResult
from app.services.provider_normalize import normalize_provider_name
from app.services.provider_router import submit_render_task


# =========================
# Helpers
# =========================
def _safe_json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        loaded = json.loads(value)
        return loaded if isinstance(loaded, dict) else {}
    except json.JSONDecodeError:
        return {}


def _build_callback_url(provider: str) -> str:
    normalized_provider = normalize_provider_name(provider)

    if settings.provider_callback_use_relay and settings.provider_callback_public_base_url:
        relay_base = settings.provider_callback_public_base_url.rstrip("/")
        relay_path = settings.provider_callback_relay_path_template.format(provider=normalized_provider).lstrip("/")
        return f"{relay_base}/{relay_path}"

    base = settings.public_base_url.rstrip("/")
    return f"{base}/api/v1/provider-callbacks/{normalized_provider}"


def _resolve_prompt_text(raw: dict[str, Any]) -> str:
    return (
        raw.get("resolved_prompt_text")
        or raw.get("prompt_text")
        or raw.get("script_text")
        or raw.get("prompt")
        or raw.get("text")
        or ""
    ).strip()


def _resolve_duration_seconds(raw: dict[str, Any], provider: str) -> int:
    raw_duration = (
        raw.get("resolved_duration_seconds")
        or raw.get("duration_seconds")
        or raw.get("provider_target_duration_sec")
        or raw.get("target_duration_sec")
        or 5
    )

    try:
        duration = int(raw_duration)
    except (TypeError, ValueError):
        duration = 5

    normalized_provider = normalize_provider_name(provider)

    # provider-aware guardrails for Veo: keep on short validated duration buckets
    if normalized_provider == "veo":
        allowed = {4, 6, 8}
        if duration not in allowed:
            duration = 4 if duration <= 4 else 6 if duration <= 6 else 8

    return duration


def _resolve_aspect_ratio(raw: dict[str, Any]) -> str:
    value = str(
        raw.get("aspect_ratio")
        or raw.get("provider_aspect_ratio")
        or "16:9"
    ).strip()

    allowed = {"16:9", "9:16", "1:1"}
    return value if value in allowed else "16:9"


def _resolve_metadata(raw: dict[str, Any], provider: str) -> dict[str, Any]:
    metadata = raw.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}

    return {
        "scene_index": raw.get("scene_index"),
        "title": raw.get("title"),
        "source_provider": normalize_provider_name(provider),
        **metadata,
    }


# =========================
# Provider-specific payload builders
# =========================
_PROVIDER_DEFAULT_MODELS: dict[str, str] = {
    "veo": "veo_default_model",
}


def _build_provider_payload(raw: dict[str, Any], provider: str) -> dict[str, Any]:
    """Build a normalized scene dispatch payload for Veo.

    The default model is resolved from ``settings`` via ``_PROVIDER_DEFAULT_MODELS``.
    Unknown providers fall back to ``raw["provider_model"]`` with no default.
    """
    default_model_attr = _PROVIDER_DEFAULT_MODELS.get(provider)
    default_model = getattr(settings, default_model_attr) if default_model_attr else None
    return {
        "prompt_text": _resolve_prompt_text(raw),
        "negative_prompt": raw.get("negative_prompt"),
        "provider_model": raw.get("provider_model") or default_model,
        "aspect_ratio": _resolve_aspect_ratio(raw),
        "duration_seconds": _resolve_duration_seconds(raw, provider),
        "prompt_image_url": raw.get("prompt_image_url"),
        "prompt_image_gcs_uri": raw.get("prompt_image_gcs_uri"),
        "last_frame_image_url": raw.get("last_frame_image_url"),
        "last_frame_image_gcs_uri": raw.get("last_frame_image_gcs_uri"),
        "seed": raw.get("seed"),
        "enable_audio": bool(raw.get("enable_audio", False)),
        "metadata": _resolve_metadata(raw, provider),
    }


def build_scene_dispatch_payload(provider: str, request_payload_json: str) -> dict[str, Any]:
    normalized_provider = normalize_provider_name(provider)
    raw = _safe_json_loads(request_payload_json)
    return _build_provider_payload(raw, normalized_provider)


# =========================
# Public entrypoint
# =========================
def get_dispatch_runtime_override() -> dict[str, Any]:
    """Load runtime override for dispatch worker with safe defaults."""
    try:
        with SessionLocal() as db:
            row = get_or_create_worker_override(db, queue_name="render.dispatch")
            return {
                "dispatch_batch_limit": int(row.dispatch_batch_limit or settings.default_dispatch_batch_limit),
                "poll_countdown_seconds": int(row.poll_countdown_seconds or settings.default_poll_countdown_seconds),
                "enabled": bool(row.enabled),
            }
    except Exception:
        return {
            "dispatch_batch_limit": int(settings.default_dispatch_batch_limit),
            "poll_countdown_seconds": int(settings.default_poll_countdown_seconds),
            "enabled": True,
        }


async def dispatch_scene_task(provider: str, request_payload_json: str) -> NormalizedSubmitResult:
    normalized_provider = normalize_provider_name(provider)
    scene_payload = build_scene_dispatch_payload(normalized_provider, request_payload_json)
    callback_url = _build_callback_url(normalized_provider)

    try:
        return await submit_render_task(
            provider=normalized_provider,
            scene_payload=scene_payload,
            callback_url=callback_url,
        )
    except Exception as exc:
        return NormalizedSubmitResult(
            accepted=False,
            provider=normalized_provider,
            provider_model=scene_payload.get("provider_model"),
            callback_url_used=callback_url,
            raw_response=None,
            error_message=str(exc),
        )