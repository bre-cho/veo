"""hook_engine — generates the opening hook (first 3–15 seconds).

Uses the psychological strategy chosen by ``decision_engine`` so that each
hook is grounded in a deliberate retention mechanic, not a random template.
"""
from __future__ import annotations

from typing import Any, Dict

from app.drama.script.engines.decision_engine import select_hook_strategy

_HOOK_TEMPLATES: Dict[str, str] = {
    "delayed_reveal": "It already happened… you just didn't notice.",
    "time_pressure": "By the time they realized what was happening… it was already too late.",
    "invisible_threat": "Everything looked normal… until you realize it was never normal at all.",
    "question_loop": "Why would someone do that? The answer changes everything.",
    "escalation_tease": "What started as nothing… was about to become everything.",
    "normal_to_abnormal": "Everything looked normal… until it wasn't.",
}

_DEFAULT_HOOK = "Something was about to change everything."


def generate_hook(
    drama_state: Dict[str, Any],
    scene_context: Dict[str, Any],
) -> tuple[str, str]:
    """Return ``(hook_text, strategy_name)``."""
    strategy = select_hook_strategy(drama_state, scene_context)
    hook = _HOOK_TEMPLATES.get(strategy, _DEFAULT_HOOK)
    return hook, strategy
