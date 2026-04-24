from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class TensionScoreBreakdown:
    goal_collision: float
    hidden_agenda_asymmetry: float
    emotional_exposure_risk: float
    power_imbalance: float
    unresolved_prior_memory: float
    time_pressure: float
    social_consequence: float

    @property
    def total(self) -> float:
        return round(
            self.goal_collision
            + self.hidden_agenda_asymmetry
            + self.emotional_exposure_risk
            + self.power_imbalance
            + self.unresolved_prior_memory
            + self.time_pressure
            + self.social_consequence,
            2,
        )


class TensionEngine:
    """Computes scene-level tension from intent, relationships, and beat context.

    Scores are heuristic placeholders designed for later replacement with a learned model.
    """

    def score(
        self,
        intents: List[Any],
        relationship_snapshots: Iterable[Any],
        scene_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        scene_context = scene_context or {}
        relationships = list(relationship_snapshots)

        goal_collision = min(len(intents) * 8.0, 20.0)
        hidden_agenda_asymmetry = min(sum(getattr(r, "hidden_agenda_score", 0.0) for r in relationships) * 0.5, 15.0)
        emotional_exposure_risk = float(scene_context.get("exposure_risk", 8.0))
        power_imbalance = min(sum(abs(getattr(r, "dominance_source_over_target", 0.0)) for r in relationships) * 0.4, 15.0)
        unresolved_prior_memory = float(scene_context.get("unresolved_prior_memory", 6.0))
        time_pressure = float(scene_context.get("time_pressure", 5.0))
        social_consequence = float(scene_context.get("social_consequence", 6.0))

        breakdown = TensionScoreBreakdown(
            goal_collision=goal_collision,
            hidden_agenda_asymmetry=hidden_agenda_asymmetry,
            emotional_exposure_risk=emotional_exposure_risk,
            power_imbalance=power_imbalance,
            unresolved_prior_memory=unresolved_prior_memory,
            time_pressure=time_pressure,
            social_consequence=social_consequence,
        )

        return {
            "tension_score": breakdown.total,
            "breakdown": asdict(breakdown),
            "flat_scene": breakdown.total < 35.0,
        }
