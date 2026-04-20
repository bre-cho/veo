"""ExperimentWinnerInjector — push winning variant metadata into scoring layer."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.services.channel_engine import ChannelEngine
    from app.services.learning_engine import PerformanceLearningEngine


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ExperimentWinnerInjector:
    """Reads experiment winner from PerformanceLearningEngine and propagates it.

    ``inject()`` calls ``experiment_summary()``, identifies the winner variant,
    then:
    1. Upserts a ``ScoringCalibration`` row reflecting the winner's metadata.
    2. Adjusts the ChannelEngine's weight profile so future plan generation
       biases toward the winner's hook/cta patterns.
    """

    def inject(
        self,
        db: Session,
        learning_store: "PerformanceLearningEngine",
        experiment_id: str,
        channel_engine: "ChannelEngine",
    ) -> dict[str, Any]:
        """Inject winning variant metadata into calibration and channel weights.

        Returns a summary dict with ``winner_variant_id``, ``injected`` bool,
        and ``calibration_id`` when a row was upserted.
        """
        summary = learning_store.experiment_summary(experiment_id=experiment_id)
        winner_variant_id: str | None = summary.get("winner_variant_id")
        variants: list[dict[str, Any]] = summary.get("variants", [])

        if not winner_variant_id or not variants:
            return {"winner_variant_id": None, "injected": False, "reason": "no_data"}

        winner_variant = next((v for v in variants if v["variant_id"] == winner_variant_id), None)
        if winner_variant is None:
            return {"winner_variant_id": winner_variant_id, "injected": False, "reason": "variant_missing"}

        # Collect winner record metadata from all records matching this variant
        all_records = learning_store.all_records()
        winner_records = [
            r for r in all_records
            if r.get("experiment_id") == experiment_id and r.get("variant_id") == winner_variant_id
        ]

        hook_pattern: str | None = None
        cta_pattern: str | None = None
        avatar_id: str | None = None
        product_id: str | None = None
        platform: str | None = None
        product_category: str | None = None

        if winner_records:
            sample = winner_records[0]
            hook_pattern = sample.get("hook_pattern")
            cta_pattern = sample.get("cta_pattern")
            avatar_id = sample.get("avatar_id")
            product_id = sample.get("product_id")
            platform = sample.get("platform")

        # 1. Upsert ScoringCalibration
        calibration_id: str | None = None
        try:
            from app.models.scoring_calibration import ScoringCalibration

            weights: dict[str, Any] = {
                "hook_pattern": hook_pattern,
                "cta_pattern": cta_pattern,
                "avatar_id": avatar_id,
                "product_id": product_id,
                "winner_avg_score": winner_variant.get("avg_score"),
                "sample_count": winner_variant.get("sample_count", 0),
            }
            existing = (
                db.query(ScoringCalibration)
                .filter(
                    ScoringCalibration.platform == platform,
                    ScoringCalibration.product_category == product_category,
                )
                .first()
            )
            if existing:
                existing.weights = weights
                existing.sample_count = winner_variant.get("sample_count", 0)
                existing.calibrated_at = _now()
                calibration = existing
            else:
                calibration = ScoringCalibration(
                    platform=platform,
                    product_category=product_category,
                    weights=weights,
                    sample_count=winner_variant.get("sample_count", 0),
                )
                db.add(calibration)

            db.commit()
            db.refresh(calibration)
            calibration_id = calibration.id
        except Exception:
            pass

        # 2. Nudge channel engine weights toward winner patterns
        try:
            if hasattr(channel_engine, "_adaptive_weight_adjustments"):
                adj: dict[str, float] = getattr(channel_engine, "_adaptive_weight_adjustments", {})
                if hook_pattern:
                    adj[f"hook_pattern:{hook_pattern}"] = 0.05
                channel_engine._adaptive_weight_adjustments = adj  # type: ignore[attr-defined]
        except Exception:
            pass

        return {
            "winner_variant_id": winner_variant_id,
            "injected": True,
            "hook_pattern": hook_pattern,
            "cta_pattern": cta_pattern,
            "avatar_id": avatar_id,
            "product_id": product_id,
            "calibration_id": calibration_id,
        }
