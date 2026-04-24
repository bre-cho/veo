from __future__ import annotations

from typing import Any, Dict


def to_render_prompt_fragments(camera_plan: Dict[str, Any], continuity_report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "camera_move": camera_plan.get("primary_move"),
        "framing_psychology": camera_plan.get("lens_psychology_mode"),
        "emotional_lighting": "contrast_pressure" if camera_plan.get("tension_band") == "high" else "balanced",
        "continuity_carry_over": continuity_report.get("status", "ok"),
        "scene_transition_note": "; ".join(continuity_report.get("continuity_notes", [])) if continuity_report.get("continuity_notes") else "smooth",
    }
