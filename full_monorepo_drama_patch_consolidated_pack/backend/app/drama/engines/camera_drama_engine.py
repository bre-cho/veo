from __future__ import annotations

from typing import Any, Dict, List, Optional


class CameraDramaEngine:
    """Translates dramatic state into camera psychology.

    The output is intentionally adapter-friendly so downstream render providers can
    map these tokens into Veo/Runway/Kling/native prompt grammars.
    """

    def build_camera_plan(
        self,
        scene_context: Dict[str, Any],
        tension_breakdown: Dict[str, Any],
        power_shift: Dict[str, Any],
        blocking_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        tension_score = float(tension_breakdown.get("tension_score", 0.0))
        exposure_risk = float(tension_breakdown.get("exposure_risk", 0.0))
        dominant_character_id = power_shift.get("dominant_character_id")
        emotional_center_id = scene_context.get("emotional_center_character_id")

        move = self._select_move(tension_score, exposure_risk, power_shift)
        shot = self._select_primary_shot(tension_score, power_shift)
        reveal_timing = self._select_reveal_timing(exposure_risk, tension_score)

        return {
            "scene_id": scene_context.get("scene_id"),
            "primary_move": move,
            "primary_shot": shot,
            "dominant_character_id": dominant_character_id,
            "emotional_center_character_id": emotional_center_id,
            "focus_order": self._focus_order(scene_context, dominant_character_id, emotional_center_id),
            "lens_psychology_mode": self._lens_mode(tension_score, exposure_risk),
            "reveal_timing": reveal_timing,
            "movement_strategy": self._movement_strategy(move, tension_score),
            "eye_line_strategy": self._eye_line_strategy(power_shift, blocking_plan),
            "render_bridge_tokens": self._render_bridge_tokens(move, shot, tension_score, exposure_risk),
            "camera_notes": self._camera_notes(move, shot, reveal_timing),
        }

    def _select_move(self, tension_score: float, exposure_risk: float, power_shift: Dict[str, Any]) -> str:
        if power_shift.get("outcome_type") in {"moral_power_flip", "dominance_flip"}:
            return "push_in_then_reframe"
        if exposure_risk > 0.75:
            return "controlled_push_in"
        if tension_score > 80:
            return "handheld_pressure_track"
        if tension_score > 55:
            return "slow_arc"
        return "static_or_micro_dolly"

    def _select_primary_shot(self, tension_score: float, power_shift: Dict[str, Any]) -> str:
        if power_shift.get("outcome_type") == "moral_power_flip":
            return "eye_level_close_reveal"
        if tension_score > 75:
            return "tight_over_shoulder"
        if tension_score > 55:
            return "medium_two_shot_with_axis_tension"
        return "clean_eye_level_master"

    def _select_reveal_timing(self, exposure_risk: float, tension_score: float) -> str:
        if exposure_risk > 0.75:
            return "late_hold_on_reaction"
        if tension_score > 70:
            return "turning_point_emphasis"
        return "progressive_disclosure"

    def _focus_order(
        self,
        scene_context: Dict[str, Any],
        dominant_character_id: Optional[str],
        emotional_center_id: Optional[str],
    ) -> List[str]:
        ordered: List[str] = []
        if dominant_character_id:
            ordered.append(str(dominant_character_id))
        if emotional_center_id and str(emotional_center_id) not in ordered:
            ordered.append(str(emotional_center_id))
        for participant in scene_context.get("participants", []):
            cid = str(participant.get("character_id") or participant.get("id") or "")
            if cid and cid not in ordered:
                ordered.append(cid)
        return ordered

    def _lens_mode(self, tension_score: float, exposure_risk: float) -> str:
        if exposure_risk > 0.75:
            return "claustrophobic_revelation"
        if tension_score > 80:
            return "instability_under_pressure"
        if tension_score > 55:
            return "relationship_readability_with_depth"
        return "neutral_clarity"

    def _movement_strategy(self, move: str, tension_score: float) -> Dict[str, Any]:
        return {
            "mode": move,
            "speed": "slow" if tension_score < 70 else "measured_tense",
            "stability": "controlled" if "handheld" not in move else "volatile_controlled",
        }

    def _eye_line_strategy(self, power_shift: Dict[str, Any], blocking_plan: Dict[str, Any]) -> str:
        if power_shift.get("outcome_type") in {"moral_power_flip", "dominance_flip"}:
            return "break_then_restore_hierarchy"
        if blocking_plan.get("spatial_mode") == "triangular_distance":
            return "fragmented_loyalties"
        return "clean_hierarchy"

    def _render_bridge_tokens(self, move: str, shot: str, tension_score: float, exposure_risk: float) -> Dict[str, Any]:
        return {
            "camera_move": move,
            "shot_type": shot,
            "tension_band": "high" if tension_score >= 75 else "mid" if tension_score >= 50 else "low",
            "exposure_mode": "high" if exposure_risk >= 0.7 else "standard",
        }

    def _camera_notes(self, move: str, shot: str, reveal_timing: str) -> List[str]:
        return [
            f"Use {move} as the primary motion grammar.",
            f"Anchor the scene with {shot} for readable power dynamics.",
            f"Time the emotional reveal using {reveal_timing} rather than decorative cutting.",
        ]
