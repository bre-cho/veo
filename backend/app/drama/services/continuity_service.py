from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from app.drama.engines.continuity_engine import ContinuityEngine

if TYPE_CHECKING:
    from app.drama.models.scene_drama_state import DramaSceneState


class ContinuityService:
    """Thin orchestration layer for continuity checks.

    Replace in-memory lookup stubs with repository/database calls when integrating
    into the target monorepo.
    """

    def __init__(self) -> None:
        self.engine = ContinuityEngine()

    def inspect_scene_transition(
        self,
        scene_context: Dict[str, Any],
        current_analysis: Dict[str, Any],
        previous_scene_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        previous_scene_state = previous_scene_state or {}
        return self.engine.inspect_transition(
            previous_scene_state=previous_scene_state,
            current_scene_context=scene_context,
            current_analysis=current_analysis,
        )

    def compare(self, previous_state: DramaSceneState, current_state: DramaSceneState) -> Dict[str, Any]:
        """Compare two scene states and detect continuity breaks."""
        previous_dict = {
            "scene_goal": previous_state.scene_goal,
            "visible_conflict": previous_state.visible_conflict,
            "hidden_conflict": previous_state.hidden_conflict,
            "scene_temperature": previous_state.scene_temperature,
            "pressure_level": previous_state.pressure_level,
            "dominant_character_id": str(previous_state.dominant_character_id) if previous_state.dominant_character_id else None,
            "emotional_center_character_id": str(previous_state.emotional_center_character_id) if previous_state.emotional_center_character_id else None,
            "outcome_type": previous_state.outcome_type,
            "power_shift_delta": previous_state.power_shift_delta,
            "trust_shift_delta": previous_state.trust_shift_delta,
            "exposure_shift_delta": previous_state.exposure_shift_delta,
            "dependency_shift_delta": previous_state.dependency_shift_delta,
        }
        
        current_dict = {
            "scene_goal": current_state.scene_goal,
            "visible_conflict": current_state.visible_conflict,
            "hidden_conflict": current_state.hidden_conflict,
            "scene_temperature": current_state.scene_temperature,
            "pressure_level": current_state.pressure_level,
            "dominant_character_id": str(current_state.dominant_character_id) if current_state.dominant_character_id else None,
            "emotional_center_character_id": str(current_state.emotional_center_character_id) if current_state.emotional_center_character_id else None,
            "outcome_type": current_state.outcome_type,
            "power_shift_delta": current_state.power_shift_delta,
            "trust_shift_delta": current_state.trust_shift_delta,
            "exposure_shift_delta": current_state.exposure_shift_delta,
            "dependency_shift_delta": current_state.dependency_shift_delta,
        }
        
        # Use the engine to inspect the transition
        analysis_result = self.engine.inspect_transition(
            previous_scene_state=previous_dict,
            current_scene_context=current_dict,
            current_analysis={},
        )
        
        # Determine if there's a continuity break
        has_break = False
        if analysis_result.get("continuity_status") != "ok":
            has_break = True
        elif previous_state.outcome_type and current_state.scene_goal:
            # If previous outcome doesn't align with current goal, mark as break
            has_break = previous_state.outcome_type not in [current_state.scene_goal, current_state.visible_conflict, current_state.hidden_conflict]
        
        return {
            "has_break": has_break,
            "previous_state_summary": previous_dict,
            "current_state_summary": current_dict,
            "analysis": analysis_result,
        }
