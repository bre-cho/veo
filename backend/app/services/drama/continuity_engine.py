"""continuity_engine — manages drama continuity across scenes and episodes.

Ensures that:
1. Character states are correctly carried forward between scenes.
2. Memory traces inform current scene acting.
3. Relationship deltas are accumulated correctly.
4. Arc progression is consistent.
"""
from __future__ import annotations

from typing import Any


class DramaContinuityEngine:
    """Propagates drama state forward across scene/episode boundaries."""

    def carry_forward_state(
        self,
        character_state: dict[str, Any],
        previous_scene_outcome: str | None,
        memory_traces: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Prepare a character's state for the next scene.

        Applies decay to volatile values (tension, anger) and integrates
        memory trace signals.

        Returns
        -------
        Updated character state dict.
        """
        state = dict(character_state)

        # Natural decay of volatile states between scenes
        _DECAY_FIELDS = {
            "anger_level": 0.05,
            "fear_level": 0.03,
            "internal_conflict_level": 0.04,
            "goal_pressure_level": 0.02,
            "current_secret_load": 0.02,
        }
        for field, decay in _DECAY_FIELDS.items():
            if field in state:
                state[field] = round(max(0.0, float(state[field]) - decay), 3)

        # Memory trace activation
        if memory_traces:
            total_weight = sum(float(m.get("emotional_weight") or 0.0) for m in memory_traces)
            trust_pull = sum(float(m.get("trust_impact") or 0.0) for m in memory_traces)
            shame_pull = sum(float(m.get("shame_impact") or 0.0) for m in memory_traces)

            if abs(trust_pull) > 0.05 and "trust_level" in state:
                state["trust_level"] = round(
                    max(0.0, min(1.0, float(state["trust_level"]) + trust_pull * 0.5)), 3
                )
            if shame_pull > 0.05 and "shame_level" in state:
                state["shame_level"] = round(
                    min(1.0, float(state["shame_level"]) + shame_pull * 0.3), 3
                )

        state["updated_from_previous_scene"] = True
        return state

    def fetch_relevant_memories(
        self,
        character_id: str,
        recall_trigger: str | None,
        memory_traces: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Return memory traces relevant to the current scene trigger."""
        if not recall_trigger:
            return []
        return [
            m for m in memory_traces
            if m.get("character_id") == character_id
            and (
                m.get("recall_trigger") == recall_trigger
                or m.get("event_type") == recall_trigger
            )
        ]

    def validate_scene_law(self, scene_drama: dict[str, Any]) -> list[str]:
        """Check SCENE LAW: every scene must have at least one shift.

        Also checks flat_scene if tension data is included.

        Returns
        -------
        list of violation strings (empty = compliant).
        """
        violations: list[str] = []
        shifts = [
            "power_shift_delta",
            "trust_shift_delta",
            "exposure_shift_delta",
            "dependency_shift_delta",
        ]
        has_shift = any(abs(float(scene_drama.get(s) or 0.0)) > 0.01 for s in shifts)
        if not has_shift:
            violations.append("SCENE_LAW: no measurable shift detected — scene is flat")

        # Flat-scene flag from tension analysis
        if scene_drama.get("flat_scene") is True:
            violations.append(
                "FLAT_SCENE: tension score below threshold — consider adding conflict"
            )

        return violations
