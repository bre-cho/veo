from __future__ import annotations

from typing import Any


class AvatarScorecardService:
    """Additive-first wrapper around any existing avatar scoring heuristics."""

    def build_predicted_scorecard(self, *, avatar_id, context: dict[str, Any]) -> dict[str, float]:
        # TODO: wire to existing avatar identity/continuity/voice engines.
        return {
            "predicted_score": 0.70,
            "predicted_ctr": 0.06,
            "predicted_retention": 0.62,
            "predicted_conversion": 0.01,
            "continuity_score": 0.80,
            "brand_fit_score": 0.75,
        }

    def build_actual_scorecard(self, *, outcome: dict[str, Any]) -> dict[str, float | None]:
        return {
            "actual_ctr": outcome.get("actual_ctr"),
            "actual_retention": outcome.get("actual_retention"),
            "actual_watch_time": outcome.get("actual_watch_time"),
            "actual_conversion": outcome.get("actual_conversion"),
            "actual_publish_score": outcome.get("actual_publish_score"),
        }
