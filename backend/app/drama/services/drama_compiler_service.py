from __future__ import annotations

from typing import Any, Dict, Optional

from app.drama.engines.blocking_engine import BlockingEngine
from app.drama.engines.camera_drama_engine import CameraDramaEngine
from app.drama.engines.arc_engine import ArcEngine
from app.drama.services.continuity_service import ContinuityService


class DramaCompilerService:
    """Compiles scene analysis into render-bridge payloads.

    This service does not render. It assembles deterministic drama outputs that a
    downstream prompt compiler or animation layer can consume.
    """

    def __init__(self) -> None:
        self.blocking_engine = BlockingEngine()
        self.camera_engine = CameraDramaEngine()
        self.continuity_service = ContinuityService()
        self.arc_engine = ArcEngine()

    def compile_scene(
        self,
        scene_context: Dict[str, Any],
        scene_analysis: Dict[str, Any],
        previous_scene_state: Optional[Dict[str, Any]] = None,
        character_arc_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        tension_breakdown = scene_analysis.get("tension_breakdown", {})
        power_shift = scene_analysis.get("power_shift", {})
        relationship_snapshot = scene_analysis.get("relationship_snapshot", {})

        blocking_plan = self.blocking_engine.build_plan(
            scene_context=scene_context,
            tension_breakdown=tension_breakdown,
            power_shift=power_shift,
            relationship_snapshot=relationship_snapshot,
        )
        camera_plan = self.camera_engine.build_camera_plan(
            scene_context=scene_context,
            tension_breakdown=tension_breakdown,
            power_shift=power_shift,
            blocking_plan=blocking_plan,
        )
        continuity_report = self.continuity_service.inspect_scene_transition(
            scene_context=scene_context,
            current_analysis=scene_analysis,
            previous_scene_state=previous_scene_state,
        )
        arc_update = None
        if character_arc_state:
            arc_update = self.arc_engine.advance_arc(character_arc_state, scene_analysis)

        return {
            "scene_id": scene_context.get("scene_id"),
            "blocking_plan": blocking_plan,
            "camera_plan": camera_plan,
            "continuity_report": continuity_report,
            "arc_update": arc_update,
            "render_bridge_payload": self._render_bridge_payload(scene_context, scene_analysis, blocking_plan, camera_plan),
        }

    def _render_bridge_payload(
        self,
        scene_context: Dict[str, Any],
        scene_analysis: Dict[str, Any],
        blocking_plan: Dict[str, Any],
        camera_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "scene_id": scene_context.get("scene_id"),
            "dramatic_temperature": scene_analysis.get("tension_breakdown", {}).get("tension_score"),
            "camera_tokens": camera_plan.get("render_bridge_tokens", {}),
            "blocking_mode": blocking_plan.get("spatial_mode"),
            "focus_order": camera_plan.get("focus_order", []),
            "notes": [
                "Use drama compile output as source-of-truth for render prompt generation.",
                "Do not override power hierarchy with decorative camera movement.",
            ],
        }
