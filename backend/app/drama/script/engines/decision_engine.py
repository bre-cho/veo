"""decision_engine — selects a psychological hook strategy from drama state.

Instead of picking a template sentence directly, this engine chooses a
*strategy* that downstream hook/narration engines can render into text.

Two public API functions:
- ``select_hook_strategy`` — used by the single-scene ``ScriptEngine``.
- ``select_story_strategy`` — used by the multi-scene ``NextLevelScriptEngine``;
  uses the expanded strategy vocabulary and updated thresholds.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def select_hook_strategy(
    drama_state: Dict[str, Any],
    scene_context: Dict[str, Any],
) -> str:
    """Return the hook strategy for a single-scene script.

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


def select_story_strategy(
    drama_state: Dict[str, Any],
    scene_context: Dict[str, Any],
) -> str:
    """Return the story strategy for a multi-scene (next-level) script.

    Uses an expanded strategy vocabulary with adjusted thresholds that work
    well for longer-form content (15+ minute episodes).

    Priority order:
    1. Betrayal outcome → delayed_betrayal_reveal
    2. High tension + hidden conflict → invisible_threat
    3. High tension (≥75) → pressure_escalation
    4. Default → normal_to_abnormal
    """
    outcome_type: Optional[str] = drama_state.get("outcome_type")
    tension_score: float = float(drama_state.get("tension_score", 0))
    hidden_conflict: Optional[str] = (
        scene_context.get("hidden_conflict")
        if isinstance(scene_context, dict)
        else None
    )

    if outcome_type == "betrayal":
        return "delayed_betrayal_reveal"

    if tension_score >= 85 and hidden_conflict:
        return "invisible_threat"

    if tension_score >= 75:
        return "pressure_escalation"

    return "normal_to_abnormal"
