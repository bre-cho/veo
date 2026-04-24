from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


class PowerShiftEngine:
    """Computes scene outcome deltas across multiple power dimensions."""

    def compute(
        self,
        scene_context: Optional[Dict[str, Any]] = None,
        relationship_snapshots: Optional[Iterable[Any]] = None,
    ) -> Dict[str, Any]:
        scene_context = scene_context or {}
        relationships = list(relationship_snapshots or [])

        avg_dom = 0.0
        if relationships:
            avg_dom = sum(float(getattr(r, "dominance_source_over_target", 0.0) or 0.0) for r in relationships) / len(relationships)

        trigger = scene_context.get("trigger_event", "scene_turn")
        exposure_risk = float(scene_context.get("exposure_risk", 0.3))

        return {
            "trigger_event": trigger,
            "social_delta": round(avg_dom * -0.1, 3),
            "emotional_delta": round(exposure_risk * 0.2, 3),
            "informational_delta": round(exposure_risk * 0.15, 3),
            "moral_delta": round(scene_context.get("moral_reversal", 0.0), 3),
            "spatial_delta": round(scene_context.get("spatial_shift", 0.0), 3),
            "narrative_control_delta": round(scene_context.get("narrative_control_shift", 0.1), 3),
        }
