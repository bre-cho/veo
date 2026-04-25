"""ab_test_engine — generates A/B hook variants and selects the best one.

Produces multiple hook candidates per story strategy, then scores them using
a deterministic heuristic so the engine can pick the strongest opening line
without requiring an external model call.
"""
from __future__ import annotations

from typing import Dict, List

_HOOK_VARIANTS: Dict[str, List[str]] = {
    "delayed_betrayal_reveal": [
        "It already happened… you just didn't notice.",
        "The betrayal was already in motion before anyone saw it.",
        "By the time the truth appeared, the damage was done.",
    ],
    "invisible_threat": [
        "Everything looked normal… until one detail changed everything.",
        "No one saw the threat because it was hiding in plain sight.",
        "The danger was not coming. It was already there.",
    ],
    "pressure_escalation": [
        "By the time they understood what was happening… it was too late.",
        "Every choice made the situation worse.",
        "The clock was already running out.",
    ],
    # Carry-over strategies from single-scene engine for full compatibility
    "delayed_reveal": [
        "It already happened… you just didn't notice.",
        "The moment had already passed. Nobody caught it.",
        "By the time they looked back, it was too late to change anything.",
    ],
    "time_pressure": [
        "By the time they realized what was happening… it was already too late.",
        "The window to stop it had already closed.",
        "Every second they waited, the situation got worse.",
    ],
    "question_loop": [
        "Why would someone do that? The answer changes everything.",
        "One question kept coming back. No one wanted to answer it.",
        "There was something nobody was saying. And everyone felt it.",
    ],
    "escalation_tease": [
        "What started as nothing… was about to become everything.",
        "Small things. Until they weren't.",
        "It began with one detail that didn't fit.",
    ],
}

_DEFAULT_VARIANTS: List[str] = [
    "Everything looked normal… until it wasn't.",
    "At first, nobody thought it mattered.",
    "The first sign was easy to miss.",
]

_HIGH_IMPACT_WORDS = frozenset(["truth", "too late", "danger", "betrayal", "secret", "wrong"])


def generate_hook_variants(strategy: str) -> List[str]:
    """Return the list of hook candidates for the given strategy.

    Falls back to ``_DEFAULT_VARIANTS`` for unknown strategies.
    """
    return list(_HOOK_VARIANTS.get(strategy, _DEFAULT_VARIANTS))


def _score_hook(hook: str) -> int:
    """Heuristic score for a single hook line (higher = stronger opening)."""
    points = 0
    # Suspense markers
    if "..." in hook or "…" in hook:
        points += 2
    # High-impact vocabulary
    hook_lower = hook.lower()
    for word in _HIGH_IMPACT_WORDS:
        if word in hook_lower:
            points += 3
            break  # only award once
    # Brevity bonus (≤14 words reads faster → better hook)
    if len(hook.split()) <= 14:
        points += 2
    return points


def select_best_hook(hooks: List[str]) -> str:
    """Return the hook with the highest heuristic score.

    On a tie, the first candidate is preferred (maintains determinism).
    """
    if not hooks:
        return _DEFAULT_VARIANTS[0]
    return max(hooks, key=_score_hook)
