from __future__ import annotations

from typing import Any, Dict


def build_tts_payload(scene: Dict[str, Any]) -> Dict[str, Any]:
    """Build a TTS request payload from a render scene dict."""
    voice_directive = scene.get("voice_directive", {})

    return {
        "text": scene.get("voiceover_text"),
        "duration_sec": scene.get("duration_sec"),
        "performance": {
            "tone": voice_directive.get("tone"),
            "speed": voice_directive.get("speed"),
            "pause": voice_directive.get("pause"),
            "stress_words": voice_directive.get("stress_words", []),
        },
    }
