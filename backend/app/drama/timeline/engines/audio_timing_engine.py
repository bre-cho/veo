from __future__ import annotations

from typing import Any, Dict, List


def compile_audio_timing(render_scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build per-scene audio track timing from an ordered list of render scenes."""
    audio_tracks: List[Dict[str, Any]] = []
    cursor = 0

    for scene in render_scenes:
        duration = scene.get("duration_sec", 6)

        # Shift any per-word timestamps from scene-local to global timeline offsets.
        local_words = scene.get("word_timings", [])
        global_words = [
            {
                "word": w["word"],
                "start_sec": round(cursor + w["start_sec"], 2),
                "end_sec": round(cursor + w["end_sec"], 2),
            }
            for w in local_words
        ]

        audio_tracks.append({
            "scene_id": scene.get("scene_id"),
            "voiceover_text": scene.get("voiceover_text"),
            "start_sec": cursor,
            "end_sec": cursor + duration,
            "duration_sec": duration,
            "voice_directive": scene.get("voice_directive", {}),
            "word_timings": global_words,
        })

        cursor += duration

    return audio_tracks
