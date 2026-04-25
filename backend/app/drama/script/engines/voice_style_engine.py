"""voice_style_engine — selects TTS/voice acting directives per segment."""
from __future__ import annotations

from typing import Any, Dict


def select_voice_style(drama_state: Dict[str, Any]) -> str:
    """Return a global voice style description for the scene."""
    tension: float = float(drama_state.get("tension_score", 0))
    if tension > 80:
        return "low, slow, controlled, suspenseful"
    if tension > 60:
        return "measured, slightly tense, deliberate"
    return "neutral documentary"


def apply_voice_pattern(segment: Dict[str, Any], tension: float) -> Dict[str, str]:
    """Return a ``VoiceDirective``-compatible dict for one segment."""
    purpose = segment.get("purpose", "")
    intent = segment.get("intent", "hint")

    if tension > 80:
        return {"pause": "long", "speed": "slow", "tone": "low"}

    if purpose in ("reveal", "twist", "cliffhanger"):
        return {"pause": "long", "speed": "slow", "tone": "low"}

    if intent in ("destabilize", "mislead"):
        return {"pause": "normal", "speed": "slow", "tone": "low"}

    if intent == "dominate":
        return {"pause": "short", "speed": "normal", "tone": "intense"}

    return {"pause": "normal", "speed": "normal", "tone": "neutral"}
