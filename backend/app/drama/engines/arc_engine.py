from __future__ import annotations

from typing import Any, Dict


class ArcEngine:
    """Advances character arc stages using explainable scene outcome rules."""

    ARC_ORDER = [
        "mask_stable",
        "pressure_crack",
        "defensive_escalation",
        "first_exposure",
        "collapse_or_rupture",
        "truth_encounter",
        "reorganization",
        "transformed_state",
    ]

    def advance_arc(
        self,
        character_arc_state: Dict[str, Any],
        scene_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        current_stage = character_arc_state.get("arc_stage", "mask_stable")
        tension_score = float(scene_analysis.get("tension_breakdown", {}).get("tension_score", 0.0))
        exposure_risk = float(scene_analysis.get("tension_breakdown", {}).get("exposure_risk", 0.0))
        outcome_type = scene_analysis.get("power_shift", {}).get("outcome_type")

        next_stage = current_stage
        if exposure_risk > 0.75 and current_stage in {"mask_stable", "pressure_crack", "defensive_escalation"}:
            next_stage = "first_exposure"
        elif outcome_type in {"moral_power_flip", "dominance_flip"} and tension_score > 75:
            next_stage = "collapse_or_rupture"
        elif character_arc_state.get("truth_acceptance_level", 0.0) > 0.7:
            next_stage = "truth_encounter"

        return {
            "character_id": character_arc_state.get("character_id"),
            "previous_stage": current_stage,
            "next_stage": next_stage,
            "pressure_index": min(1.0, float(character_arc_state.get("pressure_index", 0.0)) + tension_score / 200.0),
            "transformation_index": self._transformation_index(character_arc_state, next_stage),
            "notes": self._notes(current_stage, next_stage),
        }

    def _transformation_index(self, character_arc_state: Dict[str, Any], next_stage: str) -> float:
        base = float(character_arc_state.get("transformation_index", 0.0))
        if next_stage != character_arc_state.get("arc_stage"):
            return min(1.0, base + 0.15)
        return base

    def _notes(self, current_stage: str, next_stage: str):
        if current_stage == next_stage:
            return ["Arc remains in current stage; preserve continuity rather than forcing visible change."]
        return [f"Advance arc from {current_stage} to {next_stage} with a readable transition beat."]
