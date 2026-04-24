from __future__ import annotations

from typing import Any, Dict, Optional

from app.drama.engines.blocking_engine import BlockingEngine
from app.drama.engines.camera_drama_engine import CameraDramaEngine
from app.drama.engines.arc_engine import ArcEngine
from app.drama.services.continuity_service import ContinuityService
from app.drama.services.prompt_bridge_service import PromptBridgeService


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
        self.prompt_bridge_service = PromptBridgeService()

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

    # Compatibility entrypoint used by workers.
    def compile_scene_payload(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        scene_context = analysis.get("scene_context") or {
            "scene_id": analysis.get("scene_id"),
        }
        return self.compile_scene(scene_context=scene_context, scene_analysis=analysis)

    def compile_episode(self, scene_rows: list[Dict[str, Any]]) -> Dict[str, Any]:
        compiled_scenes: list[Dict[str, Any]] = []
        continuity_warnings: list[Dict[str, Any]] = []

        previous_analysis: Dict[str, Any] | None = None
        for row in scene_rows:
            scene_context = row.get("scene_context") or {"scene_id": row.get("scene_id")}
            scene_analysis = row.get("analysis_payload") or row.get("analysis") or {}
            compiled = self.compile_scene(
                scene_context=scene_context,
                scene_analysis=scene_analysis,
                previous_scene_state=(previous_analysis.get("drama_state") if previous_analysis else None),
            )
            compiled_scenes.append(compiled)
            report = compiled.get("continuity_report") or {}
            if report.get("status") not in {"ok", "stable"}:
                continuity_warnings.append({"scene_id": compiled.get("scene_id"), "report": report})
            previous_analysis = scene_analysis

        return {
            "scene_count": len(scene_rows),
            "compiled_scenes": compiled_scenes,
            "continuity_warnings": continuity_warnings,
        }

    def compile_project(self, episode_rows: list[Dict[str, Any]]) -> Dict[str, Any]:
        compiled_scenes: list[Dict[str, Any]] = []
        continuity_warnings: list[Dict[str, Any]] = []
        episode_count = len(episode_rows)

        for episode in episode_rows:
            result = self.compile_episode(episode.get("scenes", []))
            compiled_scenes.extend(result["compiled_scenes"])
            continuity_warnings.extend(result["continuity_warnings"])

        return {
            "episode_count": episode_count,
            "scene_count": len(compiled_scenes),
            "compiled_scenes": compiled_scenes,
            "continuity_warnings": continuity_warnings,
        }

    def _render_bridge_payload(
        self,
        scene_context: Dict[str, Any],
        scene_analysis: Dict[str, Any],
        blocking_plan: Dict[str, Any],
        camera_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        continuity_report = self.continuity_service.inspect_scene_transition(
            scene_context=scene_context,
            current_analysis=scene_analysis,
            previous_scene_state=None,
        )
        return self.prompt_bridge_service.build_render_bridge_payload(
            scene_context=scene_context,
            scene_analysis=scene_analysis,
            blocking_plan=blocking_plan,
            camera_plan=camera_plan,
            continuity_report=continuity_report,
        )
