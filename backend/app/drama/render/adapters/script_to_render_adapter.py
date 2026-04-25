from __future__ import annotations

from typing import Any, Dict, List


class ScriptToRenderAdapter:
    """Adapts script engine output into a list of render-ready scene payloads."""

    def adapt(self, script_output: Dict[str, Any]) -> List[Dict[str, Any]]:
        render_scenes: List[Dict[str, Any]] = []

        for index, segment in enumerate(script_output.get("segments", [])):
            voice = segment.get("voice", {})

            render_scenes.append({
                "scene_index": index,
                "scene_id": segment.get("scene_id"),
                "render_purpose": segment.get("purpose"),

                "voiceover_text": segment.get("text"),
                "duration_sec": segment.get("duration_sec", 6),

                "voice_directive": {
                    "tone": voice.get("tone", "documentary, calm"),
                    "speed": voice.get("speed", "normal"),
                    "pause": voice.get("pause", "normal"),
                    "stress_words": voice.get("stress_words", []),
                },

                "drama_metadata": {
                    "subtext": segment.get("subtext"),
                    "intent": segment.get("intent"),
                    "emotion": segment.get("emotion"),
                },
            })

        return render_scenes
