"""ScoringCalibrationApplier — inject persisted calibration weights at runtime.

Reads ``ScoringCalibration`` rows for a given (campaign, platform, goal) context
and patches weight multipliers into ``ConversionScoringEngine`` and
``MultiObjectiveScorer`` before scoring, closing the calibration feedback loop.
"""
from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Staleness threshold: calibrations older than this are ignored
_MAX_CALIBRATION_AGE_DAYS = 14

# Mapping from ConversionScoringEngine dimension names to MultiObjectiveScorer
# objective names (where they overlap).
_DIMENSION_TO_OBJECTIVE: dict[str, str] = {
    "cta_quality": "conversion",
    "platform_fit": "ctr",
}


class ScoringCalibrationApplier:
    """Load and apply persisted calibration weights at score-time.

    Usage (ConversionScoringEngine)::

        applier = ScoringCalibrationApplier(db=db)
        weights = applier.get_dimension_weights(platform="tiktok", product_category="skincare")
        # weights is a dict[str, float] or None

    Usage (MultiObjectiveScorer)::

        objectives = applier.get_objective_weights(
            base_objectives={"conversion": 0.5, "ctr": 0.3, "roas": 0.2},
            platform="tiktok",
        )
        scorer = MultiObjectiveScorer(objectives)
    """

    def __init__(self, db: "Session | None" = None) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # ConversionScoringEngine dimensions
    # ------------------------------------------------------------------

    def get_dimension_weights(
        self,
        platform: str | None = None,
        product_category: str | None = None,
    ) -> dict[str, float] | None:
        """Return calibrated dimension weights for ``ConversionScoringEngine``.

        Returns ``None`` when no fresh calibration is available, signalling the
        engine should use its static defaults.
        """
        if self._db is None:
            return None
        try:
            from app.services.commerce.conversion_scoring_engine import (
                ConversionScoringEngine,
            )

            weights = ConversionScoringEngine.load_calibrated_weights(
                self._db,
                platform=platform,
                product_category=product_category,
            )
            if weights is None:
                return None
            return weights
        except Exception as exc:
            logger.debug("ScoringCalibrationApplier.get_dimension_weights failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # MultiObjectiveScorer objectives
    # ------------------------------------------------------------------

    def get_objective_weights(
        self,
        base_objectives: dict[str, float],
        platform: str | None = None,
        product_category: str | None = None,
    ) -> dict[str, float]:
        """Return a (possibly calibrated) objectives dict for ``MultiObjectiveScorer``.

        Overlapping dimension scores are mapped from persisted calibration:
        - ``cta_quality`` → ``conversion`` objective
        - ``platform_fit`` → ``ctr`` objective

        Falls back to ``base_objectives`` when no calibration is available.
        """
        dim_weights = self.get_dimension_weights(
            platform=platform, product_category=product_category
        )
        if not dim_weights:
            return base_objectives

        updated = dict(base_objectives)
        for dim, obj in _DIMENSION_TO_OBJECTIVE.items():
            if dim in dim_weights and obj in updated:
                # Blend: 60% calibrated signal, 40% original base weight
                updated[obj] = round(
                    0.6 * dim_weights[dim] + 0.4 * updated[obj], 4
                )
        return updated

    # ------------------------------------------------------------------
    # Calibration sweep
    # ------------------------------------------------------------------

    def run_calibration_sweep(
        self,
        platform: str | None = None,
        product_category: str | None = None,
    ) -> dict[str, Any]:
        """Trigger a full calibration sweep and persist updated weights.

        Returns a summary dict with ``platform``, ``product_category``,
        ``weights``, and ``sample_count``.
        """
        if self._db is None:
            return {"ok": False, "error": "db_unavailable"}
        try:
            from app.services.commerce.conversion_scoring_engine import (
                ConversionScoringEngine,
            )

            weights = ConversionScoringEngine.calibrate_weights(
                self._db,
                platform=platform,
                product_category=product_category,
            )
            return {
                "ok": True,
                "platform": platform,
                "product_category": product_category,
                "weights": weights,
            }
        except Exception as exc:
            logger.exception(
                "ScoringCalibrationApplier.run_calibration_sweep failed: %s", exc
            )
            return {"ok": False, "error": str(exc)}
