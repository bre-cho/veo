from __future__ import annotations

from app.core.runtime_paths import render_paths


class AssetResolver:
    """Resolves filesystem paths for scene videos, audio, subtitles and final output."""

    def resolve_scene_video(self, scene_id: str) -> str:
        return render_paths.scene_video_path(scene_id)

    def resolve_scene_audio(self, scene_id: str) -> str:
        return render_paths.scene_audio_path(scene_id)

    def resolve_output_path(self, project_id: str, episode_id: str) -> str:
        return render_paths.episode_output_path(project_id, episode_id)

    def resolve_subtitle_path(self, project_id: str, episode_id: str) -> str:
        """Return the ASS subtitle file path for the given project/episode."""
        return render_paths.episode_subtitle_path(project_id, episode_id)
