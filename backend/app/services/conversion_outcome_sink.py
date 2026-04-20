"""ConversionOutcomeSink — ingest real conversion outcomes into VariantRunRecord."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from app.models.variant_run_record import VariantRunRecord
from app.services.learning_engine import _BOOST_MIN_RECORDS

if TYPE_CHECKING:
    from app.services.learning_engine import PerformanceLearningEngine


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ConversionOutcomeSink:
    """Ingest real conversion outcomes and optionally trigger a re-score.

    ``ingest()`` finds the VariantRunRecord matching the given ``variant_id``
    (looked up via ``context->variant_id``), updates its outcome columns, and
    triggers a lightweight re-score in the PerformanceLearningEngine when the
    sample_size threshold is met.
    """

    def ingest(
        self,
        db: Session,
        learning_store: "PerformanceLearningEngine",
        variant_id: str,
        conversion_rate: float,
        revenue_attributed: float = 0.0,
        click_through_rate: float = 0.0,
    ) -> dict[str, Any]:
        """Update VariantRunRecord and conditionally trigger a re-score.

        Returns a result dict with ``updated``, ``rescored``, and the record id.
        """
        # Find matching record via context->variant_id
        row: VariantRunRecord | None = (
            db.query(VariantRunRecord)
            .filter(
                VariantRunRecord.context["variant_id"].as_string() == variant_id
            )
            .first()
        )

        if row is None:
            return {"updated": False, "reason": "record_not_found", "variant_id": variant_id}

        # Update outcome columns
        row.actual_conversion_score = conversion_rate
        row.actual_ctr = click_through_rate
        row.outcome_recorded_at = _now()

        # Store revenue in context (no dedicated column)
        ctx: dict[str, Any] = dict(row.context or {})
        ctx["revenue_attributed"] = revenue_attributed
        row.context = ctx

        db.add(row)
        db.commit()
        db.refresh(row)

        # Check sample size for re-score trigger
        rescored = False
        experiment_id: str | None = ctx.get("experiment_id")
        if experiment_id:
            try:
                all_records = learning_store.all_records()
                matching = [r for r in all_records if r.get("experiment_id") == experiment_id]
                if len(matching) >= _BOOST_MIN_RECORDS:
                    # Re-record with updated conversion score to influence adaptive scoring
                    sample = next(
                        (r for r in matching if r.get("variant_id") == variant_id), None
                    )
                    if sample:
                        learning_store.record(
                            video_id=f"rescore:{row.id}",
                            hook_pattern=sample.get("hook_pattern", "unknown"),
                            cta_pattern=sample.get("cta_pattern", "unknown"),
                            template_family=sample.get("template_family", "unknown"),
                            conversion_score=conversion_rate,
                            platform=sample.get("platform"),
                            market_code=sample.get("market_code"),
                            experiment_id=experiment_id,
                            variant_id=variant_id,
                        )
                        rescored = True
            except Exception:
                pass

        return {
            "updated": True,
            "rescored": rescored,
            "record_id": row.id,
            "variant_id": variant_id,
            "conversion_rate": conversion_rate,
        }
