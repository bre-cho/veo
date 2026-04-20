"""VariantHistoryService — query layer on VariantRunRecord."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.variant_run_record import VariantRunRecord


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class VariantHistoryService:
    """Query helper for VariantRunRecord with experiment-level aggregation."""

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

        Returns the winner row, or None if no matching records exist.
        """
        rows = self.list_variants(db, experiment_id)
        if not rows:
            return None

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
