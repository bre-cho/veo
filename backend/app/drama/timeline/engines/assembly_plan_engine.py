from __future__ import annotations

from typing import Any, Dict, List


def build_assembly_plan(
    project_id: str,
    episode_id: str,
    scenes: List[Dict[str, Any]],
    audio_tracks: List[Dict[str, Any]],
    subtitle_tracks: List[Dict[str, Any]],
    transition_map: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build the final assembly plan that describes how all tracks are combined."""
    return {
        "project_id": project_id,
        "episode_id": episode_id,
        "video_tracks": scenes,
        "audio_tracks": audio_tracks,
        "subtitle_tracks": subtitle_tracks,
        "transition_map": transition_map,
        "output": {
            "format": "mp4",
            "resolution": "1920x1080",
            "fps": 24,
            "audio_codec": "aac",
            "video_codec": "h264",
        },
    }
