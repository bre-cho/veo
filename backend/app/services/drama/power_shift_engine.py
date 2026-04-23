"""power_shift_engine — detects and quantifies power shifts between characters.

A power shift occurs when a scene outcome changes who holds authority,
information, or emotional control in a relationship.
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Outcome → shift mapping
# ---------------------------------------------------------------------------

_OUTCOME_SHIFTS: dict[str, dict[str, float]] = {
    "betrayal": {
        "trust_shift_delta": -0.25,
        "resentment_level": +0.2,
        "recent_betrayal_score": +0.4,
    },
    "victory": {
        "dominance_source_over_target": +0.15,
        "fear_level": +0.1,
    },
    "exposure": {
        "exposure_shift_delta": +0.3,
        "shame_level": +0.2,
        "mask_strength": -0.15,
    },
    "confession": {
        "trust_shift_delta": +0.1,
        "openness_level": +0.2,
        "mask_strength": -0.1,
    },
    "collapse": {
        "dominance_source_over_target": -0.2,
        "vulnerability_level": +0.25,
        "dependency_shift_delta": +0.15,
    },
    "reconciliation": {
        "trust_shift_delta": +0.15,
        "resentment_level": -0.1,
        "unresolved_tension_score": -0.2,
    },
    "rejection": {
        "trust_shift_delta": -0.1,
        "dominance_source_over_target": -0.1,
        "resentment_level": +0.1,
    },
    "neutral": {},
}


class PowerShiftEngine:
    """Detects and quantifies power shifts for a scene outcome."""

    def compute(
        self,
        beat: dict[str, Any],
        scene_drama: dict[str, Any],
        relationships: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Return a list of PowerShiftSchema-compatible dicts.

        Parameters
        ----------
        beat:
            Story beat.
        scene_drama:
            Partial scene drama state from tension engine.
        relationships:
            All relationship edges for the scene.

        Returns
        -------
        list of power shift dicts.
        """
        outcome_type = str(beat.get("outcome_type") or scene_drama.get("outcome_type") or "neutral")
        deltas = _OUTCOME_SHIFTS.get(outcome_type, {})

        shifts: list[dict[str, Any]] = []

        dominant_id = scene_drama.get("dominant_character_id")
        threatened_id = scene_drama.get("threatened_character_id")

        if dominant_id and threatened_id and deltas:
            magnitude = max(abs(v) for v in deltas.values()) if deltas else 0.0
            shifts.append({
                "from_character_id": dominant_id,
                "to_character_id": threatened_id,
                "shift_type": outcome_type,
                "magnitude": round(magnitude, 3),
                "trigger_event": beat.get("type"),
                "camera_cue": self._camera_cue(outcome_type, magnitude),
                "relationship_deltas": deltas,
            })

        return shifts

    def _camera_cue(self, outcome_type: str, magnitude: float) -> str:
        if outcome_type == "exposure":
            return "close_push_in"
        if outcome_type in {"betrayal", "collapse"}:
            return "static_wide_negative_space"
        if outcome_type == "victory" and magnitude > 0.1:
            return "low_angle_forward_blocking"
        if outcome_type == "confession":
            return "tight_close_static"
        return "neutral_medium"

    def apply_deltas_to_relationship(
        self,
        relationship: dict[str, Any],
        outcome_type: str,
    ) -> dict[str, Any]:
        """Apply standard deltas to a relationship edge dict and return updated copy."""
        updated = dict(relationship)
        deltas = _OUTCOME_SHIFTS.get(outcome_type, {})
        for key, delta in deltas.items():
            if key in updated:
                updated[key] = round(max(0.0, min(1.0, float(updated[key]) + delta)), 3)
        return updated
