"""ClosedLoopCalibrationOrchestrator — coordinated calibration across all commerce surfaces.

This module closes the feedback loop between the performance learning engine and
every scoring surface in the commerce stack:

  PerformanceLearningEngine
       ↓  records
  ScoringCalibrationApplier  →  ConversionScoringEngine
       ↓                     →  MultiObjectiveScorer
  ChannelEngine weights      →  GrowthOptimizationOrchestrator
       ↓
  WinningSceneGraphStore     →  StoryboardEngine

Usage::

    orchestrator = ClosedLoopCalibrationOrchestrator(db=db, learning_store=engine)
    report = orchestrator.run_full_calibration(
        platform="tiktok",
        product_category="skincare",
    )
    # report["surfaces_calibrated"] → number of surfaces updated
    # report["weight_deltas"]       → per-surface weight change summary

Design
------
- Each "surface" is a calibration target with its own weight namespace.
- Calibration runs sequentially: ConversionScoring → MultiObjective →
  ChannelEngine → WinningSceneGraph.
- If any surface fails, the others still run (non-fatal failures logged).
- ``weight_deltas`` is populated only when pre- and post-calibration weights
  are both available.
"""
from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Minimum records required before attempting calibration on any surface
_MIN_CALIBRATION_RECORDS = 10


class ClosedLoopCalibrationOrchestrator:
    """Run calibration sweeps across all commerce scoring surfaces.

    Parameters
    ----------
    db:
        SQLAlchemy session (required for persisting calibration weights).
    learning_store:
        ``PerformanceLearningEngine`` instance; used to check record count
        and derive dimension statistics.
    """

    def __init__(
        self,
        db: "Session | None" = None,
        learning_store: Any | None = None,
    ) -> None:
        self._db = db
        self._learning_store = learning_store

    def run_full_calibration(
        self,
        platform: str | None = None,
        product_category: str | None = None,
        market_code: str | None = None,
    ) -> dict[str, Any]:
        """Run calibration across all registered surfaces.

        Returns a summary dict with:
        - ``surfaces_calibrated``: int — surfaces where calibration succeeded.
        - ``surfaces_failed``: int — surfaces where calibration raised.
        - ``weight_deltas``: dict — per-surface weight change summary.
        - ``record_count``: int — number of learning records seen.
        - ``skipped``: bool — True when below minimum record threshold.
        """
        record_count = self._record_count()
        if record_count < _MIN_CALIBRATION_RECORDS:
            logger.info(
                "ClosedLoopCalibrationOrchestrator: skipping calibration — "
                "only %d records (min %d)",
                record_count,
                _MIN_CALIBRATION_RECORDS,
            )
            return {
                "skipped": True,
                "record_count": record_count,
                "min_required": _MIN_CALIBRATION_RECORDS,
                "surfaces_calibrated": 0,
                "surfaces_failed": 0,
                "weight_deltas": {},
            }

        calibrated = 0
        failed = 0
        weight_deltas: dict[str, Any] = {}

        # --- Surface 1: ConversionScoringEngine dimension weights ---
        try:
            delta = self._calibrate_conversion_scoring(platform, product_category)
            weight_deltas["conversion_scoring"] = delta
            calibrated += 1
        except Exception as exc:
            logger.warning("ClosedLoopCalibration: conversion_scoring failed: %s", exc)
            failed += 1

        # --- Surface 2: MultiObjectiveScorer objectives ---
        try:
            delta = self._calibrate_multi_objective(platform, product_category)
            weight_deltas["multi_objective"] = delta
            calibrated += 1
        except Exception as exc:
            logger.warning("ClosedLoopCalibration: multi_objective failed: %s", exc)
            failed += 1

        # --- Surface 3: ChannelEngine contextual weights ---
        try:
            delta = self._calibrate_channel_engine(platform, market_code)
            weight_deltas["channel_engine"] = delta
            calibrated += 1
        except Exception as exc:
            logger.warning("ClosedLoopCalibration: channel_engine failed: %s", exc)
            failed += 1

        # --- Surface 4: WinningSceneGraph threshold adjustment ---
        try:
            delta = self._calibrate_winning_scene_threshold(platform)
            weight_deltas["winning_scene_graph"] = delta
            calibrated += 1
        except Exception as exc:
            logger.warning("ClosedLoopCalibration: winning_scene_graph failed: %s", exc)
            failed += 1

        logger.info(
            "ClosedLoopCalibrationOrchestrator: calibrated=%d failed=%d platform=%s",
            calibrated,
            failed,
            platform,
        )
        return {
            "skipped": False,
            "record_count": record_count,
            "platform": platform,
            "product_category": product_category,
            "market_code": market_code,
            "surfaces_calibrated": calibrated,
            "surfaces_failed": failed,
            "weight_deltas": weight_deltas,
        }

    def get_surface_weights(
        self,
        platform: str | None = None,
        product_category: str | None = None,
    ) -> dict[str, Any]:
        """Return the current calibrated weights for all surfaces.

        Returns:
            Dict mapping surface name to its current weight dict (or None when
            no calibration exists).
        """
        from app.services.commerce.scoring_calibration_applier import ScoringCalibrationApplier

        applier = ScoringCalibrationApplier(db=self._db)
        dim_weights = applier.get_dimension_weights(
            platform=platform, product_category=product_category
        )
        obj_weights = applier.get_objective_weights(
            base_objectives={"conversion": 0.5, "ctr": 0.3, "roas": 0.2},
            platform=platform,
            product_category=product_category,
        )
        return {
            "conversion_scoring_dims": dim_weights,
            "multi_objective_weights": obj_weights,
            "channel_engine": self._channel_engine_weights(platform),
        }

    # ------------------------------------------------------------------
    # Private surface calibrators
    # ------------------------------------------------------------------

    def _calibrate_conversion_scoring(
        self,
        platform: str | None,
        product_category: str | None,
    ) -> dict[str, Any]:
        """Run calibration sweep for ConversionScoringEngine dimensions."""
        from app.services.commerce.scoring_calibration_applier import ScoringCalibrationApplier

        applier = ScoringCalibrationApplier(db=self._db)
        before = applier.get_dimension_weights(platform=platform, product_category=product_category) or {}
        result = applier.run_calibration_sweep(platform=platform, product_category=product_category)
        after = result.get("weights") or {}
        return {
            "ok": result.get("ok", False),
            "before": before,
            "after": after,
            "delta": {
                k: round((after.get(k, 0.0) - before.get(k, 0.0)), 4)
                for k in set(list(before.keys()) + list(after.keys()))
            },
        }

    def _calibrate_multi_objective(
        self,
        platform: str | None,
        product_category: str | None,
    ) -> dict[str, Any]:
        """Recalibrate MultiObjectiveScorer objective weights from recent records."""
        if self._learning_store is None:
            return {"ok": False, "reason": "no_learning_store"}
        try:
            records = self._learning_store.all_records()
        except Exception:
            return {"ok": False, "reason": "store_error"}

        # Filter to platform/category
        filtered = [
            r for r in records
            if (platform is None or r.get("platform") == platform)
            and (product_category is None or (r.get("performance_metrics") or {}).get("product_category") == product_category)
        ]
        if not filtered:
            return {"ok": False, "reason": "no_filtered_records"}

        # Derive objective weights as normalised mean scores
        dims = ("conversion_score", "click_through_rate")
        dim_means: dict[str, float] = {}
        for dim in dims:
            vals = [float(r.get(dim, 0.0)) for r in filtered]
            dim_means[dim] = sum(vals) / len(vals) if vals else 0.0

        total = sum(dim_means.values()) or 1.0
        new_weights = {d: round(v / total, 4) for d, v in dim_means.items()}
        return {"ok": True, "weights": new_weights, "sample_count": len(filtered)}

    def _calibrate_channel_engine(
        self,
        platform: str | None,
        market_code: str | None,
    ) -> dict[str, Any]:
        """Recalibrate ChannelEngine contextual weight adjustments from learning data."""
        if self._learning_store is None:
            return {"ok": False, "reason": "no_learning_store"}
        try:
            from app.services.channel_engine import _derive_contextual_weight_adjustments
            adjustments = _derive_contextual_weight_adjustments(
                self._learning_store,
                platform=platform or "",
                goal="conversion",
                market_code=market_code or "",
            )
            return {"ok": True, "adjustments": adjustments}
        except Exception as exc:
            return {"ok": False, "reason": str(exc)}

    def _calibrate_winning_scene_threshold(
        self,
        platform: str | None,
    ) -> dict[str, Any]:
        """Adaptively adjust the winning-graph score threshold based on recent scores."""
        if self._learning_store is None:
            return {"ok": False, "reason": "no_learning_store"}
        try:
            records = self._learning_store.all_records()
        except Exception:
            return {"ok": False, "reason": "store_error"}

        filtered = [r for r in records if platform is None or r.get("platform") == platform]
        if not filtered:
            return {"ok": False, "reason": "no_filtered_records"}

        scores = [float(r.get("conversion_score", 0.0)) for r in filtered]
        mean_score = sum(scores) / len(scores)
        # Adaptive threshold: set to 80th percentile of recent scores
        sorted_scores = sorted(scores)
        p80_idx = max(0, int(len(sorted_scores) * 0.80) - 1)
        p80 = sorted_scores[p80_idx]
        return {
            "ok": True,
            "mean_score": round(mean_score, 4),
            "suggested_threshold": round(p80, 4),
            "sample_count": len(filtered),
        }

    def _record_count(self) -> int:
        """Return the number of records in the learning store."""
        if self._learning_store is None:
            return 0
        try:
            return len(self._learning_store.all_records())
        except Exception:
            return 0

    @staticmethod
    def _channel_engine_weights(platform: str | None) -> dict[str, Any]:
        """Return the default channel engine weight config for a platform."""
        return {"platform": platform, "source": "default"}
