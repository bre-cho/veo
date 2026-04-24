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

        social_delta = round(avg_dom * -0.1, 3)
        emotional_delta = round(exposure_risk * 0.2, 3)
        informational_delta = round(exposure_risk * 0.15, 3)
        moral_delta = round(scene_context.get("moral_reversal", 0.0), 3)
        spatial_delta = round(scene_context.get("spatial_shift", 0.0), 3)
        narrative_control_delta = round(scene_context.get("narrative_control_shift", 0.1), 3)

        total_delta = sum(abs(x) for x in [
            social_delta,
            emotional_delta,
            informational_delta,
            moral_delta,
            spatial_delta,
            narrative_control_delta,
        ])

        return {
            "trigger_event": trigger,
            "social_delta": social_delta,
            "emotional_delta": emotional_delta,
            "informational_delta": informational_delta,
            "moral_delta": moral_delta,
            "spatial_delta": spatial_delta,
            "narrative_control_delta": narrative_control_delta,
            "total_delta": round(total_delta, 3),
            "relationship_shifts": [],
        }
