"""power_shift_engine — detects and quantifies multi-dimensional power shifts.

Section 10: Power Shift Engine
-------------------------------
Power dimensions:
  - social_power
  - emotional_power
  - informational_power
  - moral_power
  - physical/spatial_power
  - narrative_control

A character can lose social power but gain moral power in the same scene.
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Outcome → multi-dimensional shift mapping (section 10)
# ---------------------------------------------------------------------------

_OUTCOME_MULTIDIM_SHIFTS: dict[str, dict[str, float]] = {
    "betrayal": {
        "social_delta": -0.1,
        "emotional_delta": -0.2,
        "informational_delta": +0.15,   # betrayer gains info leverage
        "moral_delta": -0.25,
        "spatial_delta": 0.0,
        "narrative_control_delta": -0.1,
    },
    "victory": {
        "social_delta": +0.2,
        "emotional_delta": +0.1,
        "informational_delta": 0.0,
        "moral_delta": 0.0,
        "spatial_delta": +0.1,
        "narrative_control_delta": +0.15,
    },
    "exposure": {
        "social_delta": -0.2,
        "emotional_delta": -0.1,
        "informational_delta": -0.3,    # secret exposed = info loss
        "moral_delta": -0.1,
        "spatial_delta": -0.1,
        "narrative_control_delta": -0.2,
    },
    "confession": {
        "social_delta": -0.05,
        "emotional_delta": +0.2,        # emotional truth increases power
        "informational_delta": -0.15,
        "moral_delta": +0.2,            # moral power rises from truth
        "spatial_delta": 0.0,
        "narrative_control_delta": +0.1,
    },
    "collapse": {
        "social_delta": -0.25,
        "emotional_delta": -0.2,
        "informational_delta": -0.05,
        "moral_delta": -0.1,
        "spatial_delta": -0.15,
        "narrative_control_delta": -0.2,
    },
    "reconciliation": {
        "social_delta": +0.1,
        "emotional_delta": +0.15,
        "informational_delta": +0.05,
        "moral_delta": +0.1,
        "spatial_delta": +0.05,
        "narrative_control_delta": 0.0,
    },
    "rejection": {
        "social_delta": -0.15,
        "emotional_delta": -0.1,
        "informational_delta": 0.0,
        "moral_delta": -0.05,
        "spatial_delta": 0.0,
        "narrative_control_delta": -0.1,
    },
    "neutral": {
        "social_delta": 0.0,
        "emotional_delta": 0.0,
        "informational_delta": 0.0,
        "moral_delta": 0.0,
        "spatial_delta": 0.0,
        "narrative_control_delta": 0.0,
    },
}

# Legacy single-axis shifts kept for backwards compat
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
    """Detects and quantifies multi-dimensional power shifts for a scene outcome."""

    def compute(
        self,
        beat: dict[str, Any],
        scene_drama: dict[str, Any],
        relationships: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Return a list of PowerShiftSchema-compatible dicts (legacy single-axis).

        Use ``compute_multidim`` for the full 6-axis output.
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

    def compute_multidim(
        self,
        beat: dict[str, Any],
        scene_drama: dict[str, Any],
        relationships: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Return a list of MultiDimensionalPowerShiftSchema-compatible dicts.

        Each dimension can shift independently.  The *from* character is the
        one who currently holds more dominance; deltas are applied to them.
        """
        outcome_type = str(beat.get("outcome_type") or scene_drama.get("outcome_type") or "neutral")
        dim_shifts = _OUTCOME_MULTIDIM_SHIFTS.get(outcome_type, _OUTCOME_MULTIDIM_SHIFTS["neutral"])

        dominant_id = scene_drama.get("dominant_character_id")
        threatened_id = scene_drama.get("threatened_character_id")

        if not dominant_id or not threatened_id:
            return []

        # Scale by conflict intensity
        intensity = float(beat.get("conflict_intensity") or 0.5)
        scale = 0.5 + intensity * 0.5  # range 0.5 – 1.0

        explanation_parts: list[str] = []
        for dim, delta in dim_shifts.items():
            if abs(delta) > 0.05:
                direction = "loses" if delta < 0 else "gains"
                dim_name = dim.replace("_delta", "").replace("_", " ")
                explanation_parts.append(f"{direction} {dim_name}")

        return [{
            "scene_id": scene_drama.get("scene_id", ""),
            "from_character_id": dominant_id,
            "to_character_id": threatened_id,
            "social_delta": round(dim_shifts["social_delta"] * scale, 3),
            "emotional_delta": round(dim_shifts["emotional_delta"] * scale, 3),
            "informational_delta": round(dim_shifts["informational_delta"] * scale, 3),
            "moral_delta": round(dim_shifts["moral_delta"] * scale, 3),
            "spatial_delta": round(dim_shifts["spatial_delta"] * scale, 3),
            "narrative_control_delta": round(dim_shifts["narrative_control_delta"] * scale, 3),
            "trigger_event": outcome_type,
            "explanation": "; ".join(explanation_parts) or "no significant shift",
        }]

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
