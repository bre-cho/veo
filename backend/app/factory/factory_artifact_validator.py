from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ArtifactValidationResult:
    ok: bool
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


class FactoryArtifactValidator:
    """Validate render/audio/subtitle/manifest artifacts for factory runs."""

    def __init__(self, app_env: str | None = None) -> None:
        self.app_env = (app_env or os.getenv("APP_ENV") or "development").lower()

    def validate(
        self,
        *,
        render_job: Any | None,
        render_manifest: dict[str, Any] | str | None,
        scenes: list[dict[str, Any]],
        audio_url: str | None,
        output_video_url: str | None,
        allow_async_render: bool = False,
    ) -> ArtifactValidationResult:
        issues: list[str] = []
        warnings: list[str] = []
        details: dict[str, Any] = {}

        if render_job is None:
            issues.append("render_job_missing")

        final_url = output_video_url
        if render_job is not None:
            final_url = (
                final_url
                or getattr(render_job, "final_video_url", None)
                or getattr(render_job, "output_url", None)
            )
            details["render_status"] = getattr(render_job, "status", None)
            details["storage_key"] = getattr(render_job, "storage_key", None)

        details["output_video_url"] = final_url
        if not final_url:
            if allow_async_render and self.app_env != "production":
                warnings.append("render_output_pending_async")
            else:
                issues.append("render_output_missing")

        if final_url and not str(final_url).startswith(("http://", "https://", "s3://", "gs://")):
            path = Path(str(final_url))
            if not path.exists():
                issues.append("render_file_not_found")
            elif path.stat().st_size <= 0:
                issues.append("render_file_empty")

        manifest: dict[str, Any] | None = None
        if render_manifest:
            try:
                manifest = json.loads(render_manifest) if isinstance(render_manifest, str) else render_manifest
            except Exception as exc:  # noqa: BLE001
                issues.append(f"manifest_parse_failed:{type(exc).__name__}")
        else:
            issues.append("manifest_missing")

        if manifest:
            manifest_scenes = manifest.get("scenes") or []
            details["manifest_scene_count"] = len(manifest_scenes)
            if not manifest_scenes:
                issues.append("manifest_has_no_scenes")
            if scenes and len(manifest_scenes) != len(scenes):
                issues.append("manifest_scene_count_mismatch")

            duration = manifest.get("estimated_duration_seconds")
            if duration is None:
                duration = manifest.get("duration_seconds")
            details["estimated_duration_seconds"] = duration
            if duration is None:
                warnings.append("manifest_duration_missing")
            else:
                try:
                    if float(duration) <= 0:
                        issues.append("invalid_manifest_duration")
                except (TypeError, ValueError):
                    issues.append("invalid_manifest_duration")

            subtitle_segments = manifest.get("subtitle_segments") or []
            details["subtitle_segment_count"] = len(subtitle_segments)
            if scenes and not subtitle_segments:
                warnings.append("subtitle_segments_missing")

        details["audio_url"] = audio_url
        if not audio_url:
            warnings.append("audio_url_missing")

        return ArtifactValidationResult(
            ok=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            details=details,
        )
