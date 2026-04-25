from __future__ import annotations

from typing import Any, Dict, List


def compile_subtitle_timing(render_scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build subtitle chunks for each scene, evenly distributed within scene duration."""
    subtitles: List[Dict[str, Any]] = []
    cursor = 0

    for scene in render_scenes:
        text = scene.get("voiceover_text", "")
        duration = scene.get("duration_sec", 6)

        chunks = split_subtitle_text(text)
        chunk_duration = max(duration / max(len(chunks), 1), 1)

        local_cursor = cursor

        for idx, chunk in enumerate(chunks):
            subtitles.append({
                "scene_id": scene.get("scene_id"),
                "index": idx,
                "text": chunk,
                "start_sec": round(local_cursor, 2),
                "end_sec": round(local_cursor + chunk_duration, 2),
            })
            local_cursor += chunk_duration

        cursor += duration

    return subtitles


def split_subtitle_text(text: str) -> List[str]:
    """Split subtitle text into chunks of up to 7 words each.

    For empty input, returns a list containing the original string so that
    callers always receive at least one chunk.
    """
    words = text.split()
    chunks = [" ".join(words[i:i + 7]) for i in range(0, len(words), 7)]
    return chunks or [text]
