"""tension_engine — computes scene-level tension and pressure distribution.

Tension is a product of:
- conflict_intensity from the beat
- sum of unresolved_tension_score across all relationship edges in scene
- internal conflict levels of each character
- secret load in play
"""
from __future__ import annotations

from typing import Any


class TensionEngine:
    """Computes overall scene tension and identifies the pressure hot-spot."""

    def compute(
        self,
        beat: dict[str, Any],
        character_states: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Return tension breakdown for a scene.

        Returns
        -------
        dict with keys:
            scene_temperature: str  ("cold" / "warm" / "heated" / "explosive")
            pressure_level: float   (0–1)
            tension_sources: list[str]
            dominant_tension_type: str
        """
        base_intensity = float(beat.get("conflict_intensity") or 0.5)

        # Aggregate internal conflict from characters
        internal_sum = sum(
            float(cs.get("internal_conflict_level") or 0.0)
            for cs in character_states
        )
        internal_avg = internal_sum / max(len(character_states), 1)

        # Aggregate unresolved tension from relationships
        rel_tension_sum = sum(
            float(r.get("unresolved_tension_score") or 0.0)
            for r in relationships
        )
        rel_tension_avg = rel_tension_sum / max(len(relationships), 1)

        # Aggregate secret load
        secret_load_avg = sum(
            float(cs.get("current_secret_load") or 0.0)
            for cs in character_states
        ) / max(len(character_states), 1)

        pressure_level = min(
            1.0,
            base_intensity * 0.5
            + internal_avg * 0.2
            + rel_tension_avg * 0.2
            + secret_load_avg * 0.1,
        )

        # Temperature label
        if pressure_level >= 0.85:
            scene_temperature = "explosive"
        elif pressure_level >= 0.65:
            scene_temperature = "heated"
        elif pressure_level >= 0.4:
            scene_temperature = "warm"
        else:
            scene_temperature = "cold"

        # Dominant tension type
        tension_sources: list[str] = []
        if base_intensity > 0.7:
            tension_sources.append("conflict_intensity")
        if internal_avg > 0.5:
            tension_sources.append("internal_conflict")
        if rel_tension_avg > 0.5:
            tension_sources.append("unresolved_relationship")
        if secret_load_avg > 0.4:
            tension_sources.append("secret_burden")

        dominant_tension_type = tension_sources[0] if tension_sources else "latent"

        return {
            "scene_temperature": scene_temperature,
            "pressure_level": round(pressure_level, 3),
            "tension_sources": tension_sources,
            "dominant_tension_type": dominant_tension_type,
        }
