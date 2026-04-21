"""ModelDrivenRankingEngine — gradient-boosting style creative ranking.

Replaces/augments the linear weighted-sum scoring in MultiObjectiveScorer with
an iterative residual-reweighting approach inspired by gradient boosting:

Algorithm
---------
1. Start with uniform weights over records.
2. For each "weak learner" dimension (conversion, ctr, roas, engagement_rate,
   watch_time_ratio), compute the weighted mean for each candidate.
3. Update sample weights to emphasise mis-ranked records (boosting step).
4. Aggregate the dimension scores using an ensemble of n_rounds weak learners.
5. Normalise final ensemble scores to [0, 1].

This produces a richer ranking than a flat linear combination, rewarding
candidates that excel across multiple dimensions rather than just one.

Usage::

    engine = ModelDrivenRankingEngine(n_rounds=5)
    ranked = engine.rank(candidates, reference_records=historical_records)
    # ranked → list of dicts with original candidate + "ensemble_score" field
"""
from __future__ import annotations

import math
from typing import Any

# Default number of boosting rounds
_DEFAULT_N_ROUNDS = 5
# Learning rate for the weight update (step size for residual upsampling)
_LEARNING_RATE = 0.3
# Dimensions used as weak learners
_WEAK_LEARNER_DIMS: list[str] = [
    "conversion_score",
    "click_through_rate",
    "roas",
    "engagement_rate",
    "watch_time_ratio",
]


def _extract_dim(record: dict[str, Any], dim: str) -> float:
    """Extract a scalar dimension value from a record, normalised to [0, 1]."""
    if dim == "roas":
        metrics = record.get("performance_metrics") or {}
        raw = float(metrics.get("roas", 0.5))
        return min(1.0, max(0.0, raw / 10.0))
    if dim in ("engagement_rate", "watch_time_ratio"):
        metrics = record.get("performance_metrics") or {}
        return min(1.0, max(0.0, float(metrics.get(dim, 0.0))))
    raw = record.get(dim)
    if raw is None:
        # Try performance_metrics sub-dict
        metrics = record.get("performance_metrics") or {}
        raw = metrics.get(dim, 0.0)
    return min(1.0, max(0.0, float(raw)))


class ModelDrivenRankingEngine:
    """Iterative residual-reweighting ranking engine.

    Parameters
    ----------
    n_rounds:
        Number of boosting rounds (weak learners to aggregate).
    learning_rate:
        Step size for the weight update at each round.
    dims:
        Dimension names to use as weak learners.
    """

    def __init__(
        self,
        n_rounds: int = _DEFAULT_N_ROUNDS,
        learning_rate: float = _LEARNING_RATE,
        dims: list[str] | None = None,
    ) -> None:
        self.n_rounds = max(1, n_rounds)
        self.learning_rate = max(0.01, min(1.0, learning_rate))
        self.dims = dims or list(_WEAK_LEARNER_DIMS)

    def rank(
        self,
        candidates: list[dict[str, Any]],
        reference_records: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Rank ``candidates`` using the ensemble scoring model.

        ``reference_records`` are historical performance records used to
        calibrate dimension weights.  When absent, candidates are self-ranked.

        Returns:
            List of candidate dicts enriched with ``ensemble_score`` and
            ``rank`` fields, sorted descending by ``ensemble_score``.
        """
        if not candidates:
            return []

        # Use candidates as reference when no external records provided
        reference = reference_records if reference_records else candidates

        # Build dimension importance from reference via weighted variance
        dim_weights = self._compute_dim_weights(reference)

        # Iterative boosting over candidates
        n = len(candidates)
        # Start with uniform sample weights over candidates
        sample_weights = [1.0 / n] * n
        ensemble_scores = [0.0] * n

        for round_idx in range(self.n_rounds):
            # Compute weighted dim score for each candidate
            round_scores = self._compute_round_scores(candidates, dim_weights, sample_weights)

            # Add to ensemble (equal blending across rounds)
            for i, rs in enumerate(round_scores):
                ensemble_scores[i] += rs

            # Update sample weights: upweight candidates whose score deviates
            # from the weighted mean (pseudo-gradient boosting residual step)
            weighted_mean = sum(sample_weights[i] * round_scores[i] for i in range(n))
            residuals = [abs(round_scores[i] - weighted_mean) for i in range(n)]
            max_resid = max(residuals) or 1.0
            for i in range(n):
                norm_resid = residuals[i] / max_resid
                sample_weights[i] = sample_weights[i] * (
                    1.0 + self.learning_rate * norm_resid
                )

            # Re-normalise weights after update
            total_w = sum(sample_weights) or 1.0
            sample_weights = [w / total_w for w in sample_weights]

        # Normalise ensemble scores to [0, 1]
        max_es = max(ensemble_scores) if ensemble_scores else 1.0
        min_es = min(ensemble_scores) if ensemble_scores else 0.0
        span = (max_es - min_es) or 1.0

        result = []
        for i, cand in enumerate(candidates):
            norm_score = round((ensemble_scores[i] - min_es) / span, 4)
            result.append({**cand, "ensemble_score": norm_score})

        result.sort(key=lambda x: x["ensemble_score"], reverse=True)
        for rank, item in enumerate(result, start=1):
            item["rank"] = rank
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _compute_dim_weights(
        self, records: list[dict[str, Any]]
    ) -> dict[str, float]:
        """Compute importance weight per dimension based on variance in records.

        Dimensions with high variance carry more signal; dimensions where all
        records have the same value contribute less.  Returns normalised weights.
        """
        if not records:
            return {d: 1.0 / len(self.dims) for d in self.dims}

        variances: dict[str, float] = {}
        for dim in self.dims:
            values = [_extract_dim(r, dim) for r in records]
            n = len(values)
            mean = sum(values) / n
            var = sum((v - mean) ** 2 for v in values) / n
            variances[dim] = var

        total_var = sum(variances.values()) or 1.0
        return {d: round(v / total_var, 6) for d, v in variances.items()}

    def _compute_round_scores(
        self,
        candidates: list[dict[str, Any]],
        dim_weights: dict[str, float],
        sample_weights: list[float],
    ) -> list[float]:
        """Compute per-candidate scores for one boosting round.

        The score is a weighted sum of dimension values, where the weight of
        each dimension is its importance * the candidate's current sample weight.
        """
        scores = []
        for i, cand in enumerate(candidates):
            w = sample_weights[i]
            score = sum(
                _extract_dim(cand, dim) * dim_weights.get(dim, 0.0)
                for dim in self.dims
            )
            scores.append(score * (1.0 + w * len(candidates)))  # amplify by sample weight
        return scores
