from __future__ import annotations

from pathlib import Path


class AssetResolver:
    """Resolves filesystem paths for scene videos, audio, subtitles and final output."""

    def resolve_scene_video(self, scene_id: str) -> str:
        return f"/data/renders/scenes/{scene_id}.mp4"

    def resolve_scene_audio(self, scene_id: str) -> str:
        return f"/data/renders/audio/{scene_id}.wav"

    def resolve_output_path(self, project_id: str, episode_id: str) -> str:
        Path(f"/data/renders/final/{project_id}").mkdir(parents=True, exist_ok=True)
        return f"/data/renders/final/{project_id}/{episode_id}.mp4"

    def resolve_subtitle_path(self, project_id: str, episode_id: str) -> str:
        """Return the ASS subtitle file path for the given project/episode."""
        Path(f"/data/renders/subtitles/{project_id}").mkdir(parents=True, exist_ok=True)
        return f"/data/renders/subtitles/{project_id}/{episode_id}.ass"
