"""MultiObjectiveScorer — Pareto-weighted composite creative scoring.

Phase 1.3: supports arbitrary objective weight dicts and returns a normalised
composite score in [0, 1].
"""
from __future__ import annotations

from typing import Any


class MultiObjectiveScorer:
    """Score a performance record against a set of weighted objectives.

    Usage::

        scorer = MultiObjectiveScorer({"conversion": 0.5, "ctr": 0.3, "roas": 0.2})
        score = scorer.score(record)   # float in [0, 1]

    Objectives are normalised so weights always sum to 1.0.  Any unknown
    objective in a record falls back to 0.0.

    Supported objectives (maps to record fields):
        conversion  → conversion_score
        ctr         → click_through_rate
        roas        → performance_metrics.roas (default 0.5 if absent)

    The composite is a Pareto-weighted linear combination of the normalised
    per-objective scores, all clamped to [0, 1].
    """

    # Mapping from objective name to record field extraction logic
    _OBJECTIVE_EXTRACTORS: dict[str, str] = {
        "conversion": "conversion_score",
        "ctr": "click_through_rate",
        "roas": "_roas",  # special: read from performance_metrics
        "budget_score": "_budget_score",  # special: budget remaining / daily limit ratio
    }

    def __init__(
        self,
        objectives: dict[str, float],
        calibration_store: "Any | None" = None,
        platform: str | None = None,
        product_category: str | None = None,
    ) -> None:
        if not objectives:
            raise ValueError("objectives dict must not be empty")

        # Apply calibration when a store is provided before normalising
        effective_objectives = dict(objectives)
        if calibration_store is not None:
            try:
                effective_objectives = calibration_store.get_objective_weights(
                    base_objectives=objectives,
                    platform=platform,
                    product_category=product_category,
                )
            except Exception:
                effective_objectives = dict(objectives)

        total = sum(effective_objectives.values())
        if total <= 0:
            raise ValueError("objective weights must sum to a positive number")
        # Normalise weights to sum to 1.0
        self.objectives: dict[str, float] = {
            k: round(v / total, 6) for k, v in effective_objectives.items()
        }

    def score(self, record: dict[str, Any]) -> float:
        """Compute a normalised composite score in [0, 1] for a record.

        Each objective's value is extracted from the record and normalised
        (it is already expected to be in [0, 1]).  The composite is the
        Pareto-weighted sum.
        """
        composite = 0.0
        for obj, weight in self.objectives.items():
            value = self._extract(record, obj)
            composite += value * weight
        return round(min(1.0, max(0.0, composite)), 4)

    def score_candidates(
        self,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Score and rank a list of records.

        Returns a list of dicts with the original record plus
        ``composite_score`` field, sorted descending by score.
        """
        scored = []
        for rec in records:
            scored.append({**rec, "composite_score": self.score(rec)})
        scored.sort(key=lambda x: x["composite_score"], reverse=True)
        return scored

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract(self, record: dict[str, Any], objective: str) -> float:
        """Extract and normalise a single objective value from a record."""
        field = self._OBJECTIVE_EXTRACTORS.get(objective)
        if field == "_roas":
            metrics = record.get("performance_metrics") or {}
            raw = float(metrics.get("roas", 0.5))
            # ROAS is often > 1; normalise assuming typical range [0, 10]
            return min(1.0, max(0.0, raw / 10.0))
        if field == "_budget_score":
            # budget_score: budget_remaining / budget_daily_limit; normalised to [0,1]
            metrics = record.get("performance_metrics") or {}
            remaining = float(metrics.get("budget_remaining", 1.0))
            daily_limit = float(metrics.get("budget_daily_limit", 1.0))
            if daily_limit <= 0:
                return 0.5
            return min(1.0, max(0.0, remaining / daily_limit))
        if field is not None:
            raw = float(record.get(field, 0.0))
            return min(1.0, max(0.0, raw))
        # Unknown objective: try the record's performance_metrics directly
        metrics = record.get("performance_metrics") or {}
        raw = float(metrics.get(objective, 0.0))
        return min(1.0, max(0.0, raw))
