"""script_scoring_engine — 5-axis quality score for generated scripts.

Scores are additive and capped per axis.  The overall score is the mean of
the four named axes (hook_strength, tension_density, retention_power,
binge_potential).
"""
from __future__ import annotations

from typing import Any, Dict, List

_STRONG_OPENERS = ("It", "Everything", "By the time", "No one", "The", "Before")


def score_script(
    full_script: str,
    segments: List[Dict[str, Any]],
) -> Dict[str, int]:
    """Return a 5-axis quality scorecard for the generated script.

    Axes:
    - ``hook_strength``   — quality of the opening (0–25)
    - ``tension_density`` — presence of reveal/twist beats (0–25)
    - ``retention_power`` — word count and curiosity density (0–25)
    - ``binge_potential`` — cliffhanger + callback presence (0–25)
    - ``overall``         — mean of the four axes (0–25)

    Args:
        full_script: Joined narration text (used for word count + opener check).
        segments:    Raw segment dicts (used for purpose checks).
    """
    score: Dict[str, int] = {
        "hook_strength": 0,
        "tension_density": 0,
        "retention_power": 0,
        "binge_potential": 0,
        "overall": 0,
    }

    # Retention power — longer scripts signal richer content
    word_count = len(full_script.split())
    if word_count > 800:
        score["retention_power"] += 20
    elif word_count > 400:
        score["retention_power"] += 10

    # Curiosity density — ellipsis usage
    ellipsis_count = full_script.count("...") + full_script.count("…")
    score["retention_power"] = min(25, score["retention_power"] + min(ellipsis_count * 2, 5))

    # Binge potential — cliffhanger and callback segments
    purposes = [seg.get("purpose", "") for seg in segments]
    if "cliffhanger" in purposes:
        score["binge_potential"] += 20
    if "callback" in purposes:
        score["binge_potential"] += 5
    score["binge_potential"] = min(25, score["binge_potential"])

    # Tension density — reveal and twist beats
    if "reveal" in purposes:
        score["tension_density"] += 20
    if "twist" in purposes:
        score["tension_density"] += 5
    score["tension_density"] = min(25, score["tension_density"])

    # Hook strength — strong psychological opener
    first_words = full_script.lstrip()
    if any(first_words.startswith(opener) for opener in _STRONG_OPENERS):
        score["hook_strength"] += 20
    if "…" in full_script[:100] or "..." in full_script[:100]:
        score["hook_strength"] += 5
    score["hook_strength"] = min(25, score["hook_strength"])

    # Overall — mean of the four axes
    axes = [
        score["hook_strength"],
        score["tension_density"],
        score["retention_power"],
        score["binge_potential"],
    ]
    score["overall"] = sum(axes) // len(axes)

    return score
