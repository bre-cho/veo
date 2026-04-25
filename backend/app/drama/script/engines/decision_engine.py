"""decision_engine — selects a psychological hook strategy from drama state.

Instead of picking a template sentence directly, this engine chooses a
*strategy* that downstream hook/narration engines can render into text.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def select_hook_strategy(
    drama_state: Dict[str, Any],
    scene_context: Dict[str, Any],
) -> str:
    """Return the name of the hook strategy that best fits the scene.

    Priority order:
    1. Outcome type (strongest dramatic signal)
    2. Tension score (urgency)
    3. Hidden conflict (invisible threat)
    4. Default
    """
    outcome_type: Optional[str] = drama_state.get("outcome_type")
    tension_score: float = float(drama_state.get("tension_score", 0))
    hidden_conflict: Optional[str] = (
        scene_context.get("hidden_conflict")
        if isinstance(scene_context, dict)
        else None
    )

    if outcome_type == "betrayal":
        return "delayed_reveal"

    if tension_score > 85:
        return "time_pressure"

    if hidden_conflict:
        return "invisible_threat"

    if outcome_type in ("revelation", "confrontation"):
        return "question_loop"

    if tension_score > 60:
        return "escalation_tease"

    return "normal_to_abnormal"
