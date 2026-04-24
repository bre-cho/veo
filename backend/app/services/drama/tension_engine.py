"""tension_engine — computes scene-level tension and pressure distribution.

Section 8: Scene Tension Engine
--------------------------------
Tension Score =
  Goal Collision
+ Hidden Agenda Asymmetry
+ Emotional Exposure Risk
+ Power Imbalance
+ Unresolved Prior Memory
+ Time Pressure
+ Social Consequence

Normalised to 0–100.  ``flat_scene`` rule triggers when all key
components are below threshold simultaneously.
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Flat-scene thresholds (section 8.4)
# ---------------------------------------------------------------------------

_FLAT_GOAL_COLLISION_THRESHOLD = 0.2
_FLAT_EXPOSURE_RISK_THRESHOLD = 0.2
_FLAT_POWER_SHIFT_THRESHOLD = 0.05   # magnitude too small to matter
_FLAT_REL_SHIFT_THRESHOLD = 0.05


class TensionEngine:
    """Computes 7-component scene tension and identifies the pressure hot-spot."""

    def compute(
        self,
        beat: dict[str, Any],
        character_states: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Return tension breakdown for a scene.

        Returns
        -------
        dict compatible with ``SceneTensionSchema`` — keys:
            scene_temperature, pressure_level, tension_score (0–100),
            goal_collision, hidden_agenda_asymmetry, emotional_exposure_risk,
            power_imbalance, unresolved_prior_memory, time_pressure,
            social_consequence, tension_sources, dominant_tension_type,
            flat_scene.
        """
        # ── Component 1: Goal Collision ────────────────────────────────────
        base_intensity = float(beat.get("conflict_intensity") or 0.5)
        goal_collision = base_intensity

        # ── Component 2: Hidden Agenda Asymmetry ──────────────────────────
        # Measure spread of hidden_agenda scores across relationship edges
        hidden_agenda_scores = [
            float(r.get("hidden_agenda") or r.get("hidden_agenda_score") or 0.0)
            for r in relationships
        ]
        if hidden_agenda_scores:
            max_ha = max(hidden_agenda_scores)
            min_ha = min(hidden_agenda_scores)
            hidden_agenda_asymmetry = max_ha - min_ha
        else:
            hidden_agenda_asymmetry = 0.0

        # ── Component 3: Emotional Exposure Risk ──────────────────────────
        exposure_scores = [
            float(cs.get("shame_level") or 0.0) * 0.5
            + float(cs.get("vulnerability_level") or 0.0) * 0.3
            + float(cs.get("current_secret_load") or 0.0) * 0.2
            for cs in character_states
        ]
        emotional_exposure_risk = max(exposure_scores) if exposure_scores else 0.0

        # Edge-level shame exposure risk
        shame_edge_risk = max(
            (float(r.get("shame_exposure_risk") or 0.0) for r in relationships),
            default=0.0,
        )
        emotional_exposure_risk = min(1.0, emotional_exposure_risk + shame_edge_risk * 0.3)

        # ── Component 4: Power Imbalance ──────────────────────────────────
        dominance_levels = [
            float(cs.get("dominance_level") or 0.5)
            for cs in character_states
        ]
        if len(dominance_levels) >= 2:
            power_imbalance = max(dominance_levels) - min(dominance_levels)
        else:
            power_imbalance = 0.0

        # ── Component 5: Unresolved Prior Memory ──────────────────────────
        unresolved_rel = sum(
            float(r.get("unresolved_tension_score") or 0.0)
            for r in relationships
        ) / max(len(relationships), 1)
        betrayal_weight = sum(
            float(r.get("recent_betrayal_score") or 0.0)
            for r in relationships
        ) / max(len(relationships), 1)
        unresolved_prior_memory = min(1.0, unresolved_rel * 0.6 + betrayal_weight * 0.4)

        # ── Component 6: Time Pressure ────────────────────────────────────
        time_pressure = float(beat.get("time_pressure") or beat.get("pressure_level") or 0.3)

        # ── Component 7: Social Consequence ──────────────────────────────
        social_consequence = float(beat.get("social_consequence") or 0.0)
        # Perceived_power edges amplify social consequence
        perceived_power_avg = sum(
            float(r.get("perceived_power") or 0.5)
            for r in relationships
        ) / max(len(relationships), 1)
        social_consequence = min(1.0, social_consequence + (perceived_power_avg - 0.5) * 0.2)

        # ── Weighted aggregate → 0–100 ────────────────────────────────────
        weights = {
            "goal_collision": 0.25,
            "hidden_agenda_asymmetry": 0.15,
            "emotional_exposure_risk": 0.20,
            "power_imbalance": 0.15,
            "unresolved_prior_memory": 0.10,
            "time_pressure": 0.08,
            "social_consequence": 0.07,
        }
        components = {
            "goal_collision": goal_collision,
            "hidden_agenda_asymmetry": hidden_agenda_asymmetry,
            "emotional_exposure_risk": emotional_exposure_risk,
            "power_imbalance": power_imbalance,
            "unresolved_prior_memory": unresolved_prior_memory,
            "time_pressure": time_pressure,
            "social_consequence": social_consequence,
        }
        tension_score = sum(
            components[k] * weights[k] for k in weights
        ) * 100.0
        tension_score = round(min(100.0, tension_score), 1)

        pressure_level = round(tension_score / 100.0, 3)

        # ── Temperature label ─────────────────────────────────────────────
        if tension_score >= 85:
            scene_temperature = "explosive"
        elif tension_score >= 65:
            scene_temperature = "heated"
        elif tension_score >= 40:
            scene_temperature = "warm"
        else:
            scene_temperature = "cold"

        # ── Tension sources ───────────────────────────────────────────────
        tension_sources: list[str] = []
        if goal_collision > 0.6:
            tension_sources.append("goal_collision")
        if hidden_agenda_asymmetry > 0.4:
            tension_sources.append("hidden_agenda_asymmetry")
        if emotional_exposure_risk > 0.5:
            tension_sources.append("emotional_exposure_risk")
        if power_imbalance > 0.4:
            tension_sources.append("power_imbalance")
        if unresolved_prior_memory > 0.5:
            tension_sources.append("unresolved_prior_memory")
        if time_pressure > 0.6:
            tension_sources.append("time_pressure")
        if social_consequence > 0.5:
            tension_sources.append("social_consequence")

        dominant_tension_type = tension_sources[0] if tension_sources else "latent"

        # ── Flat scene detection (section 8.4) ────────────────────────────
        power_shift_magnitude = float(beat.get("power_shift_delta") or 0.0)
        relation_shift_magnitude = float(beat.get("relation_shift_delta") or 0.0)
        flat_scene = (
            goal_collision < _FLAT_GOAL_COLLISION_THRESHOLD
            and emotional_exposure_risk < _FLAT_EXPOSURE_RISK_THRESHOLD
            and abs(power_shift_magnitude) < _FLAT_POWER_SHIFT_THRESHOLD
            and abs(relation_shift_magnitude) < _FLAT_REL_SHIFT_THRESHOLD
        )

        return {
            "scene_temperature": scene_temperature,
            "pressure_level": pressure_level,
            "tension_score": tension_score,
            "goal_collision": round(goal_collision, 3),
            "hidden_agenda_asymmetry": round(hidden_agenda_asymmetry, 3),
            "emotional_exposure_risk": round(emotional_exposure_risk, 3),
            "power_imbalance": round(power_imbalance, 3),
            "unresolved_prior_memory": round(unresolved_prior_memory, 3),
            "time_pressure": round(time_pressure, 3),
            "social_consequence": round(social_consequence, 3),
            "tension_sources": tension_sources,
            "dominant_tension_type": dominant_tension_type,
            "flat_scene": flat_scene,
        }
