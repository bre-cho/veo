from __future__ import annotations

from typing import Any, Dict, List


def compile_audio_timing(render_scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build per-scene audio track timing from an ordered list of render scenes."""
    audio_tracks: List[Dict[str, Any]] = []
    cursor = 0

    for scene in render_scenes:
        duration = scene.get("duration_sec", 6)

        audio_tracks.append({
            "scene_id": scene.get("scene_id"),
            "voiceover_text": scene.get("voiceover_text"),
            "start_sec": cursor,
            "end_sec": cursor + duration,
            "duration_sec": duration,
            "voice_directive": scene.get("voice_directive", {}),
        })

        cursor += duration

    return audio_tracks
