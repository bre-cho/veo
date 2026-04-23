"""emotional_update_engine — applies scene outcome deltas to character state.

Implements the INNER STATE UPDATE LAW:
    scene outcome → emotional state shift → relationship shift → memory trace update → arc stage update

After each scene the engine mutates a character's state dictionary in-place
and returns the list of memory traces and relationship deltas to persist.
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Outcome → emotional state deltas
# ---------------------------------------------------------------------------

_OUTCOME_EMOTION_DELTAS: dict[str, dict[str, float]] = {
    "betrayal": {
        "trust_level": -0.2,
        "shame_level": +0.15,
        "anger_level": +0.2,
        "mask_strength": +0.1,
        "openness_level": -0.15,
    },
    "victory": {
        "dominance_level": +0.15,
        "control_level": +0.1,
        "fear_level": -0.1,
        "vulnerability_level": -0.1,
    },
    "exposure": {
        "shame_level": +0.25,
        "mask_strength": -0.2,
        "openness_level": +0.15,
        "internal_conflict_level": +0.2,
    },
    "confession": {
        "mask_strength": -0.15,
        "openness_level": +0.2,
        "internal_conflict_level": -0.15,
        "shame_level": -0.1,
    },
    "collapse": {
        "dominance_level": -0.2,
        "vulnerability_level": +0.25,
        "trust_level": -0.1,
        "control_level": -0.15,
    },
    "reconciliation": {
        "trust_level": +0.15,
        "anger_level": -0.1,
        "openness_level": +0.1,
        "internal_conflict_level": -0.1,
    },
    "rejection": {
        "trust_level": -0.1,
        "shame_level": +0.1,
        "dominance_level": -0.1,
    },
    "neutral": {},
}

# Arc stage progression rules
_ARC_STAGE_ORDER = [
    "ordinary_world",
    "call_to_change",
    "resistance",
    "forced_entry",
    "first_test",
    "false_victory",
    "crisis",
    "dark_night",
    "breakthrough",
    "transformation",
    "new_world",
]


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)


class EmotionalUpdateEngine:
    """Applies scene outcome to character state and generates memory traces."""

    def apply(
        self,
        character_id: str,
        scene_id: str,
        outcome_type: str,
        character_state: dict[str, Any],
        related_character_id: str | None = None,
        beat: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Apply outcome deltas to character_state and return update payload.

        Returns
        -------
        dict with keys:
            updated_state: updated character_state dict
            memory_trace: dict (ready to persist as DramaMemoryTrace)
            arc_stage_update: str | None
        """
        deltas = _OUTCOME_EMOTION_DELTAS.get(outcome_type, {})
        updated_state = dict(character_state)

        for field, delta in deltas.items():
            if field in updated_state:
                updated_state[field] = _clamp(float(updated_state[field]) + delta)
        updated_state["updated_from_previous_scene"] = True
        updated_state["current_power_position"] = self._power_position(updated_state)

        # Memory trace
        emotional_weight = float((beat or {}).get("conflict_intensity") or 0.5)
        memory_trace = {
            "character_id": character_id,
            "related_character_id": related_character_id,
            "source_scene_id": scene_id,
            "event_type": outcome_type,
            "emotional_weight": emotional_weight,
            "trust_impact": deltas.get("trust_level", 0.0),
            "shame_impact": deltas.get("shame_level", 0.0),
            "fear_impact": deltas.get("fear_level", 0.0),
            "dominance_impact": deltas.get("dominance_level", 0.0),
            "meaning_label": outcome_type,
            "recall_trigger": (beat or {}).get("type"),
        }

        # Arc stage update heuristic
        arc_stage_update: str | None = None
        transformation = float(updated_state.get("transformation_index") or 0.0)
        pressure = float(updated_state.get("goal_pressure_level") or 0.5)
        if outcome_type == "exposure" and updated_state.get("mask_strength", 1.0) < 0.3:
            arc_stage_update = "dark_night"
        elif outcome_type == "confession" and updated_state.get("openness_level", 0.0) > 0.7:
            arc_stage_update = "breakthrough"
        elif outcome_type == "collapse" and pressure > 0.8:
            arc_stage_update = "crisis"

        return {
            "updated_state": updated_state,
            "memory_trace": memory_trace,
            "arc_stage_update": arc_stage_update,
        }

    def _power_position(self, state: dict[str, Any]) -> str:
        dominance = float(state.get("dominance_level") or 0.5)
        vulnerability = float(state.get("vulnerability_level") or 0.3)
        if dominance > 0.7 and vulnerability < 0.3:
            return "dominant"
        if vulnerability > 0.6:
            return "exposed"
        if dominance < 0.3:
            return "submissive"
        return "neutral"
