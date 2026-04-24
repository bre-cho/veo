from __future__ import annotations

from typing import Any, Dict


def to_storyboard_enrichment(blocking_plan: Dict[str, Any], camera_plan: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "power_holder": blocking_plan.get("dominant_character_id"),
        "emotional_anchor": blocking_plan.get("emotional_center_character_id"),
        "blocking_notes": blocking_plan.get("blocking_notes", []),
        "reveal_timing": camera_plan.get("reveal_timing"),
        "shot_duration_hint": "3-5s",
    }
