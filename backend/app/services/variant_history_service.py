"""VariantHistoryService — query layer on VariantRunRecord."""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.variant_run_record import VariantRunRecord

# Minimum number of variants with actual conversion scores before a winner
# selection is considered statistically reliable.
_MIN_WINNER_SAMPLES = 3


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Sample sufficiency & confidence helpers
# ---------------------------------------------------------------------------

class WinnerSufficiencyPolicy:
    """Evaluate whether a set of variant outcomes is sufficient to declare a winner.

    ``evaluate()`` returns a dict with:
    - ``sufficient``: bool — True when enough samples with real outcomes exist.
    - ``sample_count``: int — number of variants with actual conversion scores.
    - ``confidence_score``: float in [0, 1] — normalised confidence based on
      sample size and score spread.  0.0 means undecided; 1.0 means very high
      confidence.
    - ``reason``: str — human-readable explanation.
    """

    min_samples: int = _MIN_WINNER_SAMPLES

    def evaluate(self, rows: list[VariantRunRecord]) -> dict[str, Any]:
        scored = [r for r in rows if r.actual_conversion_score is not None]
        sample_count = len(scored)

        if sample_count < self.min_samples:
            return {
                "sufficient": False,
                "sample_count": sample_count,
                "confidence_score": 0.0,
                "reason": (
                    f"only {sample_count} variants have real outcomes "
                    f"(need ≥ {self.min_samples})"
                ),
            }

        scores = [float(r.actual_conversion_score) for r in scored]  # type: ignore[arg-type]
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        std = math.sqrt(variance) if variance > 0 else 0.0

        # Confidence grows with sample count and shrinks when scores are very
        # close together (hard to tell apart) or very spread (noisy data).
        # Formula: tanh(n/3) * (1 - min(spread_penalty, 0.5))
        spread_penalty = min(std * 2.0, 0.5)  # high std → harder to pick winner
        size_factor = math.tanh(sample_count / 3.0)
        confidence_score = round(max(0.0, min(1.0, size_factor * (1.0 - spread_penalty))), 3)

        return {
            "sufficient": True,
            "sample_count": sample_count,
            "confidence_score": confidence_score,
            "reason": (
                f"{sample_count} samples, mean={mean:.3f}, std={std:.3f}"
            ),
        }


class VariantHistoryService:
    """Query helper for VariantRunRecord with experiment-level aggregation."""

    def __init__(self) -> None:
        self._sufficiency_policy = WinnerSufficiencyPolicy()

    def list_variants(
        self,
        db: Session,
        experiment_id: str,
    ) -> list[VariantRunRecord]:
        """Return all VariantRunRecords for an experiment, sorted by conversion score desc.

        Filters by ``context->experiment_id`` JSON field.  Records without an
        explicit experiment_id in context are excluded.
        """
        rows = (
            db.query(VariantRunRecord)
            .filter(
                VariantRunRecord.context["experiment_id"].as_string() == experiment_id
            )
            .order_by(VariantRunRecord.actual_conversion_score.desc().nullslast())
            .all()
        )
        return rows

    def select_winner(
        self,
        db: Session,
        experiment_id: str,
    ) -> VariantRunRecord | None:
        """Select and mark the winning VariantRunRecord for an experiment.

        Picks the record with the highest ``actual_conversion_score`` (or
        ``winner_score`` when no outcome has been recorded yet), sets
        ``winner_variant_index=0`` on it to indicate it was chosen, and
        persists the change.

        Winner selection is gated by ``WinnerSufficiencyPolicy``: when
        insufficient real-outcome samples exist, the method still marks a
        winner (so the pipeline is not blocked) but annotates the context with
        ``winner_confidence`` and ``winner_sufficient=False`` so callers can
        decide whether to act on the selection.

        Returns the winner row, or None if no matching records exist.
        """
        rows = self.list_variants(db, experiment_id)
        if not rows:
            return None

        sufficiency = self._sufficiency_policy.evaluate(rows)

        # Prefer actual_conversion_score; fall back to winner_score
        def _sort_key(r: VariantRunRecord) -> float:
            if r.actual_conversion_score is not None:
                return float(r.actual_conversion_score)
            if r.winner_score is not None:
                return float(r.winner_score)
            return 0.0

        winner = max(rows, key=_sort_key)
        winner.winner_variant_index = 0  # mark as chosen winner
        ctx: dict[str, Any] = dict(winner.context or {})
        ctx["winner_selected_at"] = _now().isoformat()
        ctx["experiment_id"] = experiment_id
        # Annotate with sufficiency/confidence so downstream consumers can gate
        # on statistical reliability before promoting a winner.
        ctx["winner_sufficient"] = sufficiency["sufficient"]
        ctx["winner_confidence"] = sufficiency["confidence_score"]
        ctx["winner_sample_count"] = sufficiency["sample_count"]
        ctx["winner_sufficiency_reason"] = sufficiency["reason"]
        winner.context = ctx
        db.add(winner)
        db.commit()
        db.refresh(winner)
        return winner

    def get_winner_weight_profile(
        self,
        db: Session,
        experiment_id: str,
    ) -> dict[str, Any]:
        """Return scoring weight profile from the winner's context.

        Extracts ``winner_score_breakdown`` from the top-scoring record and
        returns it as a weight dict.  Falls back to an empty dict when no
        winner record exists.
        """
        rows = self.list_variants(db, experiment_id)
        if not rows:
            return {}
        best = rows[0]
        breakdown: dict[str, Any] = best.winner_score_breakdown or {}
        # Normalise to a flat weight dict (strip nested structures if present)
        weights: dict[str, Any] = {}
        for k, v in breakdown.items():
            if isinstance(v, (int, float)):
                weights[k] = float(v)
        # Always include conversion context
        weights.setdefault("experiment_id", experiment_id)
        weights.setdefault("platform", best.platform)
        weights.setdefault("product_category", best.product_category)
        return weights
