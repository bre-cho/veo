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
        returns it as a weight dict, enriched with calibration readiness and
        rollout stage guidance.
        """
        rows = self.list_variants(db, experiment_id)
        if not rows:
            return {}
        best = rows[0]
        breakdown: dict[str, Any] = best.winner_score_breakdown or {}
        weights: dict[str, Any] = {}
        for k, v in breakdown.items():
            if isinstance(v, (int, float)):
                weights[k] = float(v)
        weights.setdefault("experiment_id", experiment_id)
        weights.setdefault("platform", best.platform)
        weights.setdefault("product_category", best.product_category)

        # Calibration readiness: ready when winner is sufficient and has a breakdown
        ctx: dict[str, Any] = dict(best.context or {})
        winner_sufficient = bool(ctx.get("winner_sufficient", False))
        winner_confidence = float(ctx.get("winner_confidence", 0.0))
        sample_count = int(ctx.get("winner_sample_count", 0))
        calibration_ready = winner_sufficient and bool(weights) and winner_confidence >= 0.5

        # Segment key: platform + product_category for downstream calibration lookup
        segment_key = f"{best.platform or 'all'}|{best.product_category or 'all'}"

        # Recommended rollout stage based on confidence
        if winner_confidence >= 0.9:
            recommended_rollout_stage = 100
        elif winner_confidence >= 0.75:
            recommended_rollout_stage = 50
        elif winner_confidence >= 0.5:
            recommended_rollout_stage = 10
        else:
            recommended_rollout_stage = 0

        weights["calibration_ready"] = calibration_ready
        weights["recommended_rollout_stage"] = recommended_rollout_stage
        weights["segment_key"] = segment_key
        weights["winner_confidence"] = winner_confidence
        weights["sample_count"] = sample_count
        return weights

    def get_experiment_summary(
        self,
        db: Session,
        experiment_id: str,
    ) -> dict[str, Any]:
        """Return a summary of an experiment including variant scores and winner.

        Returns:
            Dict with ``experiment_id``, ``variant_count``, ``winner_id``,
            ``winner_score``, ``avg_score``, ``sufficiency``.
        """
        rows = self.list_variants(db, experiment_id)
        if not rows:
            return {"experiment_id": experiment_id, "variant_count": 0}

        sufficiency = self._sufficiency_policy.evaluate(rows)
        scores = [
            float(r.actual_conversion_score)
            for r in rows
            if r.actual_conversion_score is not None
        ]
        avg_score = round(sum(scores) / len(scores), 4) if scores else 0.0
        winner = rows[0]  # already sorted by score desc
        return {
            "experiment_id": experiment_id,
            "variant_count": len(rows),
            "winner_id": str(winner.id),
            "winner_score": float(winner.actual_conversion_score or winner.winner_score or 0.0),
            "avg_score": avg_score,
            "sufficiency": sufficiency,
        }

    def get_winner_confidence(
        self,
        db: Session,
        experiment_id: str,
        max_age_days: int = 30,
    ) -> dict[str, Any]:
        """Return winner confidence with staleness decay and distribution penalty.

        Args:
            experiment_id: The experiment to evaluate.
            max_age_days: Data older than this is considered stale (confidence decayed).

        Returns:
            Dict with ``confidence``, ``decay_applied``, ``distribution_penalty``,
            ``effective_confidence``.
        """
        rows = self.list_variants(db, experiment_id)
        if not rows:
            return {"confidence": 0.0, "decay_applied": 0.0, "distribution_penalty": 0.0, "effective_confidence": 0.0}

        sufficiency = self._sufficiency_policy.evaluate(rows)
        base_confidence = float(sufficiency["confidence_score"])

        # Staleness decay: penalise if latest record is older than max_age_days
        decay = 0.0
        try:
            latest_ts: datetime | None = None
            for r in rows:
                ts = getattr(r, "recorded_at", None) or getattr(r, "created_at", None)
                if ts is not None:
                    if latest_ts is None or ts > latest_ts:
                        latest_ts = ts
            if latest_ts is not None:
                age_days = (_now() - latest_ts).days
                if age_days > max_age_days:
                    decay = round(min(0.5, (age_days - max_age_days) / max(max_age_days, 1) * 0.3), 3)
        except Exception:
            pass

        # Distribution penalty: penalise heavily skewed variant distributions
        distribution_penalty = 0.0
        try:
            scored_rows = [r for r in rows if r.actual_conversion_score is not None]
            if len(scored_rows) >= 2:
                scores = [float(r.actual_conversion_score) for r in scored_rows]  # type: ignore[arg-type]
                score_max = max(scores)
                score_sum = sum(scores) or 1.0
                top_share = score_max / score_sum
                # If one variant takes >80% of the score mass, apply penalty
                if top_share > 0.80:
                    distribution_penalty = round(min(0.3, (top_share - 0.80) * 1.5), 3)
        except Exception:
            pass

        effective_confidence = round(max(0.0, base_confidence - decay - distribution_penalty), 3)
        return {
            "confidence": base_confidence,
            "decay_applied": decay,
            "distribution_penalty": distribution_penalty,
            "effective_confidence": effective_confidence,
        }
