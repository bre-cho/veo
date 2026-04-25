from __future__ import annotations

from typing import Any, Dict, List


class NextLevelScriptEngine:
    """Generates a multi-scene script from a topic payload.

    Each segment carries voiceover text plus voice and drama metadata so that
    the downstream render pipeline can consume it without additional lookups.
    """

    DEFAULT_DURATION_SEC = 6

    def generate(self, payload: Any) -> Dict[str, Any]:
        if hasattr(payload, "topic"):
            topic = payload.topic or ""
            tone = payload.tone or "documentary, calm"
            num_scenes = payload.num_scenes or 5
            duration_sec = payload.duration_sec or 60
        else:
            topic = payload.get("topic", "")
            tone = payload.get("tone", "documentary, calm") or "documentary, calm"
            num_scenes = payload.get("num_scenes", 5)
            duration_sec = payload.get("duration_sec", 60)

        segments = self._build_segments(
            topic=topic,
            tone=tone or "documentary, calm",
            num_scenes=int(num_scenes),
            total_duration=int(duration_sec),
        )

        full_script = " ".join(s["text"] for s in segments)

        return {
            "full_script": full_script,
            "segments": segments,
        }

    def _build_segments(
        self,
        topic: str,
        tone: str,
        num_scenes: int,
        total_duration: int,
    ) -> List[Dict[str, Any]]:
        scene_duration = max(total_duration // max(num_scenes, 1), self.DEFAULT_DURATION_SEC)

        scene_templates = [
            {
                "scene_id": "opening",
                "purpose": "hook",
                "text": f"It already happened… you just didn't notice.",
                "subtext": "opening psychological trigger",
                "intent": "capture_attention",
                "emotion": "curiosity",
                "voice": {
                    "tone": "low, controlled, suspenseful",
                    "speed": "slow",
                    "pause": "long",
                    "stress_words": [],
                },
            },
            {
                "scene_id": "context",
                "purpose": "context",
                "text": f"Here's what's really going on with {topic}.",
                "subtext": "establishing the frame",
                "intent": "set_context",
                "emotion": "intrigue",
                "voice": {
                    "tone": tone,
                    "speed": "normal",
                    "pause": "normal",
                    "stress_words": [],
                },
            },
            {
                "scene_id": "tension",
                "purpose": "tension",
                "text": "The stakes are higher than you think.",
                "subtext": "raising the emotional pressure",
                "intent": "build_tension",
                "emotion": "unease",
                "voice": {
                    "tone": "intense, deliberate",
                    "speed": "slow",
                    "pause": "long",
                    "stress_words": ["higher"],
                },
            },
            {
                "scene_id": "reveal",
                "purpose": "reveal",
                "text": "And this is the moment everything changes.",
                "subtext": "cathartic pivot",
                "intent": "deliver_reveal",
                "emotion": "awe",
                "voice": {
                    "tone": "dramatic, rising",
                    "speed": "normal",
                    "pause": "short",
                    "stress_words": ["moment", "changes"],
                },
            },
            {
                "scene_id": "cliffhanger",
                "purpose": "cliffhanger",
                "text": "But the story doesn't end here.",
                "subtext": "binge trigger",
                "intent": "drive_retention",
                "emotion": "suspense",
                "voice": {
                    "tone": "low, mysterious",
                    "speed": "slow",
                    "pause": "very long",
                    "stress_words": ["here"],
                },
            },
        ]

        segments: List[Dict[str, Any]] = []
        for i in range(min(num_scenes, len(scene_templates))):
            seg = dict(scene_templates[i])
            seg["duration_sec"] = scene_duration
            segments.append(seg)

        return segments
