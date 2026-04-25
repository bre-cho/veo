"""voice_acting_engine — full TTS/performance directives for each segment.

Unlike the lighter ``voice_style_engine`` (which handles single-scene global
style), this engine emits per-segment voice acting instructions including
stress-word extraction for TTS emphasis markers.
"""
from __future__ import annotations

from typing import Any, Dict, List

_STRESS_KEYWORDS: List[str] = [
    "never",
    "too late",
    "secret",
    "wrong",
    "disappeared",
    "truth",
    "betrayal",
    "danger",
    "lie",
    "lost",
    "dead",
    "over",
    "already",
    "last",
]


def extract_stress_words(text: str) -> List[str]:
    """Return a list of stress-emphasis keywords found in ``text``.

    Only returns each keyword once (deduplication) and preserves the order
    in which they appear in ``_STRESS_KEYWORDS``.
    """
    text_lower = text.lower()
    return [kw for kw in _STRESS_KEYWORDS if kw in text_lower]


def apply_voice_acting(
    segment: Dict[str, Any],
    tension_score: float,
) -> Dict[str, Any]:
    """Return a ``VoiceActingMeta``-compatible dict for one segment.

    Decision tree:
    1. High tension (≥85) → low/slow/long regardless of purpose
    2. High-drama purposes (reveal, cliffhanger) → quiet/tense/medium
    3. Default → documentary/calm/normal
    """
    text: str = segment.get("text", "")
    purpose: str = segment.get("purpose", "")

    if tension_score >= 85:
        return {
            "tone": "low, controlled, suspenseful",
            "speed": "slow",
            "pause": "long",
            "stress_words": extract_stress_words(text),
        }

    if purpose in ("reveal", "cliffhanger", "twist"):
        return {
            "tone": "quiet, tense, cinematic",
            "speed": "medium-slow",
            "pause": "medium",
            "stress_words": extract_stress_words(text),
        }

    if purpose == "hook":
        return {
            "tone": "low, deliberate, captivating",
            "speed": "slow",
            "pause": "long",
            "stress_words": extract_stress_words(text),
        }

    return {
        "tone": "documentary, calm",
        "speed": "normal",
        "pause": "normal",
        "stress_words": [],
    }
