"""retention_engine — injects curiosity loops and measures retention score.

After injection the engine estimates a retention score.  If the score is below
threshold, an additional hook is appended so the script actively fights
audience drop-off.
"""
from __future__ import annotations

from typing import Any, Dict, List

_LOOP_HOOKS = [
    "But that's not even the worst part.",
    "What happened next changed everything.",
    "And this is where things stop making sense.",
    "You're not going to believe what happened next.",
    "The real story starts right here.",
]

_CURIOSITY_PHRASES = ("...", "But that's", "What happened", "And this is")

_RETENTION_THRESHOLD = 15


def inject_retention_hooks(script: str) -> List[str]:
    """Return the list of retention hook sentences to append to the script."""
    return list(_LOOP_HOOKS[:3])


def estimate_retention(script: str) -> int:
    """Heuristic retention score (higher = more engaging)."""
    score = 0
    for phrase in _CURIOSITY_PHRASES:
        if phrase in script:
            score += 10
    score += min(script.count("...") * 2, 10)
    return score


def optimize_retention(
    full_script: str,
    retention_hooks: List[str],
) -> tuple[List[str], int]:
    """Measure script retention; append an extra hook if score is too low."""
    score = estimate_retention(full_script)
    if score < _RETENTION_THRESHOLD:
        retention_hooks = list(retention_hooks) + [_LOOP_HOOKS[3]]
    return retention_hooks, score
