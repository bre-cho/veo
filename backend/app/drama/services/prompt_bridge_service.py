from __future__ import annotations

from typing import Any, Dict


class PromptBridgeService:
    """Convert drama outputs into render-consumable enrichment payload."""

    def build_render_bridge_payload(
        self,
        *,
        scene_context: Dict[str, Any],
        scene_analysis: Dict[str, Any],
        blocking_plan: Dict[str, Any],
        camera_plan: Dict[str, Any],
        continuity_report: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "acting_enrichment": {
                "dominant_character_id": scene_analysis.get("dominant_character_id"),
                "pressure_level": scene_analysis.get("tension", {}).get("breakdown", {}).get("time_pressure", 0.0),
                "tension_score": scene_analysis.get("tension", {}).get("tension_score", 0.0),
            },
            "blocking_enrichment": {
                "spatial_mode": blocking_plan.get("spatial_mode"),
                "beats": blocking_plan.get("beats", []),
                "notes": blocking_plan.get("blocking_notes", []),
            },
            "camera_enrichment": {
                "primary_shot": camera_plan.get("primary_shot"),
                "primary_move": camera_plan.get("primary_move"),
                "tokens": camera_plan.get("render_bridge_tokens", {}),
            },
            "continuity_notes": continuity_report.get("continuity_notes", []),
            "lighting_psychology": {
                "mode": "neutral_clarity" if scene_analysis.get("tension", {}).get("tension_score", 0.0) < 55 else "contrast_pressure",
            },
            "transition_hint": continuity_report.get("status", "ok"),
            "scene_id": scene_context.get("scene_id"),
        }
