from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.drama.engines.continuity_engine import ContinuityEngine
from app.drama.models.scene_drama_state import DramaSceneState

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

    def check_continuity(self, previous_analysis: Dict[str, Any], current_analysis: Dict[str, Any]) -> Dict[str, Any]:
        previous_state = previous_analysis.get("drama_state") or previous_analysis
        current_context = current_analysis.get("scene_context") or {}
        report = self.engine.inspect_transition(
            previous_scene_state=previous_state,
            current_scene_context=current_context,
            current_analysis=current_analysis,
        )
        has_break = report.get("continuity_status") not in {"ok", "stable"}
        return {
            "has_break": bool(has_break),
            "continuity_status": report.get("continuity_status", "ok"),
            "continuity_notes": report.get("continuity_notes", []),
            "details": report,
        }

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

    def apply_scene_outcome(
        self,
        *,
        db: Session,
        scene_id: UUID,
        outcome_type: str,
        turning_point: str | None = None,
        trust_shift_delta: float = 0.0,
        exposure_shift_delta: float = 0.0,
        dependency_shift_delta: float = 0.0,
        recompute_downstream: bool = True,
    ) -> Dict[str, Any]:
        scene_state = db.query(DramaSceneState).filter(DramaSceneState.scene_id == scene_id).first()
        if scene_state is None:
            raise ValueError("scene state not found")

        scene_state.outcome_type = outcome_type
        if turning_point is not None:
            scene_state.turning_point = turning_point
        scene_state.trust_shift_delta = trust_shift_delta
        scene_state.exposure_shift_delta = exposure_shift_delta
        scene_state.dependency_shift_delta = dependency_shift_delta
        current_continuity = scene_state.continuity_payload or {}
        scene_state.continuity_payload = {
            **current_continuity,
            "status": "applied",
            "outcome_type": outcome_type,
            "recompute_downstream": recompute_downstream,
        }
        db.add(scene_state)
        db.flush()

        return {
            "scene_id": str(scene_id),
            "episode_id": str(scene_state.episode_id) if scene_state.episode_id else None,
            "project_id": str(scene_state.project_id) if scene_state.project_id else None,
            "accepted": True,
            "recompute_downstream": recompute_downstream,
        }
