from __future__ import annotations

from types import SimpleNamespace

from app.factory.factory_artifact_validator import FactoryArtifactValidator


def test_artifact_validator_flags_missing_output_in_strict_mode() -> None:
    result = FactoryArtifactValidator(app_env="production").validate(
        render_job=SimpleNamespace(status="completed", storage_key=None, output_url=None),
        render_manifest={
            "scenes": [{"scene_index": 1}],
            "subtitle_segments": [{"text": "x", "start_sec": 0, "end_sec": 1}],
            "estimated_duration_seconds": 10,
        },
        scenes=[{"scene_index": 1}],
        audio_url="https://cdn/audio.mp3",
        output_video_url=None,
        allow_async_render=False,
    )

    assert result.ok is False
    assert "render_output_missing" in result.issues


def test_artifact_validator_allows_async_warning_in_dev() -> None:
    result = FactoryArtifactValidator(app_env="development").validate(
        render_job=SimpleNamespace(status="queued", storage_key=None, output_url=None),
        render_manifest={
            "scenes": [{"scene_index": 1}],
            "subtitle_segments": [],
            "estimated_duration_seconds": 8,
        },
        scenes=[{"scene_index": 1}],
        audio_url=None,
        output_video_url=None,
        allow_async_render=True,
    )

    assert "render_output_pending_async" in result.warnings
    assert "render_output_missing" not in result.issues
