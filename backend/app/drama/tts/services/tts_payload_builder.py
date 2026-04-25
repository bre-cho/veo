from __future__ import annotations

from typing import Any, Dict


def build_tts_payload(scene: Dict[str, Any]) -> Dict[str, Any]:
    """Build a TTS request payload from a render scene dict.

    Args:
        scene: A render scene dict containing at minimum:
            - ``voiceover_text`` (str): The narration text.
            - ``duration_sec`` (int): Target audio duration in seconds.
            - ``voice_directive`` (dict): Performance parameters with keys
              ``tone``, ``speed``, ``pause``, and ``stress_words``.

    Returns:
        A TTS payload dict with ``text``, ``duration_sec``, and a nested
        ``performance`` dict containing ``tone``, ``speed``, ``pause``,
        and ``stress_words``.
    """
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
