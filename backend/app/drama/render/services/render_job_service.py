from __future__ import annotations

from typing import Any, Dict, List


def create_render_job_from_script(project_id: str, script_output: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build a list of render job dicts from a script engine output that contains render_scenes."""
    render_scenes: List[Dict[str, Any]] = script_output.get("render_scenes", [])
    jobs: List[Dict[str, Any]] = []

    for scene in render_scenes:
        voice_directive = scene.get("voice_directive", {})
        drama_metadata = scene.get("drama_metadata", {})

        jobs.append({
            "project_id": project_id,
            "scene_id": scene.get("scene_id"),
            "status": "queued",

            "voiceover_text": scene.get("voiceover_text"),
            "duration_sec": scene.get("duration_sec"),

            "voice_tone": voice_directive.get("tone"),
            "voice_speed": voice_directive.get("speed"),
            "voice_pause": voice_directive.get("pause"),
            "stress_words": voice_directive.get("stress_words", []),

            "render_purpose": scene.get("render_purpose"),
            "subtext": drama_metadata.get("subtext"),
            "intent": drama_metadata.get("intent"),
            "emotion": drama_metadata.get("emotion"),
        })

    return jobs
