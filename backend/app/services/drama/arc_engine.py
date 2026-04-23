"""arc_engine — tracks and advances character arc stages.

Arc stages follow a simplified hero's journey model:
    ordinary_world → call_to_change → resistance → forced_entry →
    first_test → false_victory → crisis → dark_night → breakthrough →
    transformation → new_world

The engine advances arc stages based on accumulated pressure and
transformation indices.
"""
from __future__ import annotations

from typing import Any

_ARC_STAGES = [
    "ordinary_world",
    "call_to_change",
    "resistance",
    "forced_entry",
    "first_test",
    "false_victory",
    "crisis",
    "dark_night",
    "breakthrough",
    "transformation",
    "new_world",
]

# Minimum combined (pressure + transformation) index to advance to next stage
_ADVANCE_THRESHOLD: dict[str, float] = {
    "ordinary_world": 0.15,
    "call_to_change": 0.25,
    "resistance": 0.35,
    "forced_entry": 0.45,
    "first_test": 0.55,
    "false_victory": 0.65,
    "crisis": 0.75,
    "dark_night": 0.82,
    "breakthrough": 0.88,
    "transformation": 0.95,
}


class ArcEngine:
    """Evaluates and advances a character's arc stage."""

    def evaluate(
        self,
        arc_progress: dict[str, Any],
        scene_outcome: str,
        character_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Compute updated arc progress after a scene outcome.

        Returns
        -------
        dict with keys: arc_stage, transformation_index, pressure_index,
                        collapse_risk, mask_break_level, arc_history_entry
        """
        current_stage = str(arc_progress.get("arc_stage") or "ordinary_world")
        pressure = float(arc_progress.get("pressure_index") or 0.0)
        transformation = float(arc_progress.get("transformation_index") or 0.0)
        collapse_risk = float(arc_progress.get("collapse_risk") or 0.0)
        mask_break = float(arc_progress.get("mask_break_level") or 0.0)

        # Update pressure
        intensity = float(character_state.get("internal_conflict_level") or 0.0)
        pressure = min(1.0, round(pressure + intensity * 0.1, 3))

        # Outcome-specific transformation increments
        if scene_outcome == "breakthrough":
            transformation = min(1.0, round(transformation + 0.15, 3))
        elif scene_outcome == "confession":
            transformation = min(1.0, round(transformation + 0.1, 3))
            mask_break = min(1.0, round(mask_break + 0.15, 3))
        elif scene_outcome in {"betrayal", "exposure"}:
            pressure = min(1.0, round(pressure + 0.08, 3))
            collapse_risk = min(1.0, round(collapse_risk + 0.1, 3))
        elif scene_outcome == "collapse":
            collapse_risk = min(1.0, round(collapse_risk + 0.2, 3))
        elif scene_outcome == "reconciliation":
            collapse_risk = max(0.0, round(collapse_risk - 0.1, 3))

        # Attempt stage advance
        advance_threshold = _ADVANCE_THRESHOLD.get(current_stage, 1.0)
        combined = (pressure + transformation) / 2
        if combined >= advance_threshold:
            stage_idx = _ARC_STAGES.index(current_stage)
            if stage_idx < len(_ARC_STAGES) - 1:
                current_stage = _ARC_STAGES[stage_idx + 1]

        return {
            "arc_stage": current_stage,
            "pressure_index": pressure,
            "transformation_index": transformation,
            "collapse_risk": collapse_risk,
            "mask_break_level": mask_break,
            "arc_history_entry": {
                "scene_outcome": scene_outcome,
                "new_stage": current_stage,
                "combined_index": round(combined, 3),
            },
        }
