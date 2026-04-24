"""arc_engine — tracks and advances character arc stages.

Section 16: Arc Engine
-----------------------
Drama arc stages (section 16.1):
    mask_stable → pressure_crack → defensive_escalation → first_exposure →
    collapse_rupture → truth_encounter → reorganization → transformed_state

Arc types (section 16.2):
    control_to_vulnerability, innocence_to_corruption, dependence_to_autonomy,
    rage_to_grief, false_authority_to_collapse, hidden_shame_to_truth,
    revenge_to_emptiness

After each scene:
    - increase/decrease pressure
    - increase/decrease mask break
    - update false belief challenge
    - update relation entanglement
"""
from __future__ import annotations

from typing import Any

# Drama-specific arc stages (section 16.1)
_DRAMA_ARC_STAGES = [
    "mask_stable",
    "pressure_crack",
    "defensive_escalation",
    "first_exposure",
    "collapse_rupture",
    "truth_encounter",
    "reorganization",
    "transformed_state",
]

# Minimum combined pressure to advance to each subsequent stage
_DRAMA_ADVANCE_THRESHOLD: dict[str, float] = {
    "mask_stable": 0.15,
    "pressure_crack": 0.28,
    "defensive_escalation": 0.40,
    "first_exposure": 0.55,
    "collapse_rupture": 0.68,
    "truth_encounter": 0.80,
    "reorganization": 0.90,
}

# Legacy journey stages kept for backward compatibility
_LEGACY_ARC_STAGES = [
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

_ALL_STAGES = set(_DRAMA_ARC_STAGES) | set(_LEGACY_ARC_STAGES)

_LEGACY_ADVANCE_THRESHOLD: dict[str, float] = {
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


def _is_drama_stage(stage: str) -> bool:
    return stage in set(_DRAMA_ARC_STAGES)


class ArcEngine:
    """Evaluates and advances a character's arc stage (drama or legacy)."""

    def evaluate(
        self,
        arc_progress: dict[str, Any],
        scene_outcome: str,
        character_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Compute updated arc progress after a scene outcome.

        Supports both drama-specific stages (section 16) and legacy stages.

        Returns
        -------
        dict with keys: arc_stage, arc_type, transformation_index,
                        pressure_index, collapse_risk, mask_break_level,
                        truth_acceptance_level, false_belief_challenge_level,
                        relation_entanglement_index, arc_history_entry
        """
        current_stage = str(arc_progress.get("arc_stage") or "mask_stable")
        arc_type = str(arc_progress.get("arc_type") or "control_to_vulnerability")
        pressure = float(arc_progress.get("pressure_index") or 0.0)
        transformation = float(arc_progress.get("transformation_index") or 0.0)
        collapse_risk = float(arc_progress.get("collapse_risk") or 0.0)
        mask_break = float(arc_progress.get("mask_break_level") or 0.0)
        truth_acceptance = float(arc_progress.get("truth_acceptance_level") or 0.0)
        false_belief_challenge = float(arc_progress.get("false_belief_challenge_level") or 0.0)
        relation_entanglement = float(arc_progress.get("relation_entanglement_index") or 0.0)

        # ── Pressure update ────────────────────────────────────────────────
        intensity = float(character_state.get("internal_conflict_level") or 0.0)
        pressure = min(1.0, round(pressure + intensity * 0.1, 3))

        # ── Outcome-specific updates ──────────────────────────────────────
        if scene_outcome == "breakthrough":
            transformation = min(1.0, round(transformation + 0.15, 3))
            truth_acceptance = min(1.0, round(truth_acceptance + 0.2, 3))
            false_belief_challenge = min(1.0, round(false_belief_challenge + 0.2, 3))
        elif scene_outcome == "confession":
            transformation = min(1.0, round(transformation + 0.1, 3))
            mask_break = min(1.0, round(mask_break + 0.15, 3))
            truth_acceptance = min(1.0, round(truth_acceptance + 0.15, 3))
            false_belief_challenge = min(1.0, round(false_belief_challenge + 0.1, 3))
        elif scene_outcome in {"betrayal", "exposure"}:
            pressure = min(1.0, round(pressure + 0.08, 3))
            collapse_risk = min(1.0, round(collapse_risk + 0.1, 3))
            mask_break = min(1.0, round(mask_break + 0.08, 3))
            false_belief_challenge = min(1.0, round(false_belief_challenge + 0.08, 3))
        elif scene_outcome == "collapse":
            collapse_risk = min(1.0, round(collapse_risk + 0.2, 3))
            mask_break = min(1.0, round(mask_break + 0.2, 3))
        elif scene_outcome == "reconciliation":
            collapse_risk = max(0.0, round(collapse_risk - 0.1, 3))
            relation_entanglement = min(1.0, round(relation_entanglement + 0.1, 3))
        elif scene_outcome == "victory":
            relation_entanglement = min(1.0, round(relation_entanglement + 0.05, 3))

        # ── Stage advance ─────────────────────────────────────────────────
        use_drama_stages = _is_drama_stage(current_stage)
        stage_list = _DRAMA_ARC_STAGES if use_drama_stages else _LEGACY_ARC_STAGES
        advance_map = _DRAMA_ADVANCE_THRESHOLD if use_drama_stages else _LEGACY_ADVANCE_THRESHOLD

        advance_threshold = advance_map.get(current_stage, 1.0)
        combined = (pressure + transformation) / 2

        if combined >= advance_threshold and current_stage in stage_list:
            stage_idx = stage_list.index(current_stage)
            if stage_idx < len(stage_list) - 1:
                current_stage = stage_list[stage_idx + 1]

        return {
            "arc_stage": current_stage,
            "arc_type": arc_type,
            "pressure_index": pressure,
            "transformation_index": transformation,
            "collapse_risk": collapse_risk,
            "mask_break_level": mask_break,
            "truth_acceptance_level": truth_acceptance,
            "false_belief_challenge_level": false_belief_challenge,
            "relation_entanglement_index": relation_entanglement,
            "arc_history_entry": {
                "scene_outcome": scene_outcome,
                "new_stage": current_stage,
                "combined_index": round(combined, 3),
                "arc_type": arc_type,
            },
        }
