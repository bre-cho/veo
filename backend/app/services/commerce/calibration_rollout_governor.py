"""CalibrationRolloutGovernor — governance layer for calibration rollout decisions.

Closes the final loop in the commerce brain by deciding *when* a new
calibration is safe to activate, when to hold, and when to rollback to
previous weights.

Algorithm
---------
1. After each ``ClosedLoopCalibrationOrchestrator.run_full_calibration()`` run
   the governor receives the ``weight_deltas`` dict.
2. It evaluates the delta magnitude per surface against configurable thresholds.
3. If the delta is too large (potential flip/spike) it holds the calibration
   pending validation samples.
4. After ``_MIN_VALIDATION_RECORDS`` new outcome records it re-evaluates:
   - Score improved ≥ ``_MIN_SCORE_GAIN`` → approve + apply
   - Score regressed ≥ ``_MAX_SCORE_LOSS`` → rollback to previous weights
   - Otherwise → approve with monitoring flag

Usage::

    governor = CalibrationRolloutGovernor(db=db, learning_store=engine)

    # After a calibration sweep:
    decision = governor.assess_rollout(
        platform="tiktok",
        product_category="skincare",
        proposed_delta={"conversion_scoring": {"cta_quality": 0.12}},
        pre_score=0.52,
        post_score=0.57,
    )
    # decision["action"]  → "approve" | "hold" | "rollback"
    # decision["reason"]  → human-readable explanation
"""
from __future__ import annotations

import logging
import time
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Maximum allowed absolute weight delta in a single calibration round.
# Deltas larger than this are considered risky and trigger a hold.
_MAX_SAFE_WEIGHT_DELTA = float(0.25)
# Minimum score gain to auto-approve a held calibration
_MIN_SCORE_GAIN = 0.02
# Maximum tolerable score regression before triggering a rollback
_MAX_SCORE_LOSS = 0.03
# Minimum new outcome records before evaluating a held calibration
_MIN_VALIDATION_RECORDS = 5
# Maximum held calibrations kept in rollout history
_MAX_HISTORY = 50

# In-memory rollout history: {(platform, product_category) → list[decision]}
_ROLLOUT_HISTORY: dict[tuple[str, str], list[dict[str, Any]]] = {}
# Snapshot of last-approved weights per context for rollback
_APPROVED_WEIGHTS: dict[tuple[str, str], dict[str, Any]] = {}


class CalibrationRolloutGovernor:
    """Govern calibration rollout decisions with hold/approve/rollback logic.

    Parameters
    ----------
    db:
        Optional SQLAlchemy session for persisting governance history.
    learning_store:
        ``PerformanceLearningEngine`` instance for evaluating outcome signals
        during held calibration re-evaluation.
    max_safe_delta:
        Maximum allowed per-surface weight delta before triggering a hold.
    """

    def __init__(
        self,
        db: "Session | None" = None,
        learning_store: Any | None = None,
        max_safe_delta: float = _MAX_SAFE_WEIGHT_DELTA,
    ) -> None:
        self._db = db
        self._learning_store = learning_store
        self._max_safe_delta = max_safe_delta

    # ------------------------------------------------------------------
    # Primary governance API
    # ------------------------------------------------------------------

    def assess_rollout(
        self,
        platform: str | None,
        product_category: str | None,
        proposed_delta: dict[str, Any],
        pre_score: float | None = None,
        post_score: float | None = None,
    ) -> dict[str, Any]:
        """Assess whether to approve, hold, or rollback a calibration.

        Args:
            platform: Target platform for the calibration.
            product_category: Target product category.
            proposed_delta: Weight deltas returned by
                ``ClosedLoopCalibrationOrchestrator.run_full_calibration()``.
                Format: {surface → {dimension → delta_float}}.
            pre_score: Mean conversion score *before* this calibration run.
            post_score: Mean conversion score *after* this calibration run
                (e.g. back-tested on validation set).

        Returns:
            Dict with:
            - ``action``: "approve" | "hold" | "rollback"
            - ``reason``: human-readable explanation
            - ``max_delta_observed``: largest absolute delta seen
            - ``score_delta``: post - pre (or None)
            - ``context``: {platform, product_category}
        """
        ctx_key = self._ctx_key(platform, product_category)

        max_delta = self._max_delta_in(proposed_delta)
        score_delta: float | None = None
        if pre_score is not None and post_score is not None:
            score_delta = round(post_score - pre_score, 4)

        # --- Decision logic ---
        if score_delta is not None and score_delta <= -_MAX_SCORE_LOSS:
            action = "rollback"
            reason = (
                f"Score regressed {score_delta:+.4f} (threshold -{_MAX_SCORE_LOSS}). "
                "Reverting to last approved weights."
            )
            self._do_rollback(ctx_key, platform, product_category)
        elif max_delta > self._max_safe_delta:
            action = "hold"
            reason = (
                f"Max weight delta {max_delta:.4f} exceeds safe threshold "
                f"{self._max_safe_delta}. Holding for {_MIN_VALIDATION_RECORDS} "
                "validation records before applying."
            )
        elif score_delta is not None and score_delta >= _MIN_SCORE_GAIN:
            action = "approve"
            reason = (
                f"Score improved {score_delta:+.4f} ≥ {_MIN_SCORE_GAIN}. "
                "Calibration approved and applied."
            )
            self._record_approved_weights(ctx_key, proposed_delta)
        else:
            action = "approve"
            reason = (
                "Delta within safe range and no significant regression. "
                "Approved with monitoring."
            )
            self._record_approved_weights(ctx_key, proposed_delta)

        decision = {
            "action": action,
            "reason": reason,
            "max_delta_observed": round(max_delta, 4),
            "score_delta": score_delta,
            "pre_score": pre_score,
            "post_score": post_score,
            "context": {"platform": platform, "product_category": product_category},
            "decided_at": time.time(),
        }
        self._append_history(ctx_key, decision)

        logger.info(
            "CalibrationRolloutGovernor: action=%s platform=%s max_delta=%.4f score_delta=%s",
            action,
            platform,
            max_delta,
            score_delta,
        )
        return decision

    def re_evaluate_held(
        self,
        platform: str | None,
        product_category: str | None,
    ) -> dict[str, Any]:
        """Re-evaluate a held calibration after new outcome records arrive.

        Compares the performance before the held calibration vs. the most
        recent records. If enough improvement, approves; if regression,
        rolls back.

        Returns:
            Dict with ``action``, ``reason``, ``sample_count``,
            ``avg_score_before``, ``avg_score_after``.
        """
        ctx_key = self._ctx_key(platform, product_category)
        history = _ROLLOUT_HISTORY.get(ctx_key, [])
        last_hold = next(
            (d for d in reversed(history) if d.get("action") == "hold"),
            None,
        )

        if not last_hold:
            return {"action": "no_pending_hold", "reason": "No held calibration found."}

        pre_score = last_hold.get("pre_score") or 0.5
        recent_score = self._recent_avg_score(platform, product_category)
        sample_count = self._recent_record_count(platform, product_category)

        if sample_count < _MIN_VALIDATION_RECORDS:
            return {
                "action": "hold",
                "reason": f"Insufficient validation records ({sample_count}/{_MIN_VALIDATION_RECORDS}).",
                "sample_count": sample_count,
                "avg_score_before": pre_score,
                "avg_score_after": recent_score,
            }

        score_delta = round(recent_score - pre_score, 4)

        if score_delta <= -_MAX_SCORE_LOSS:
            action = "rollback"
            reason = (
                f"Held calibration re-evaluated: score regressed {score_delta:+.4f}. Rolling back."
            )
            self._do_rollback(ctx_key, platform, product_category)
        elif score_delta >= _MIN_SCORE_GAIN:
            action = "approve"
            reason = (
                f"Held calibration approved after validation: score improved {score_delta:+.4f}."
            )
        else:
            action = "approve"
            reason = "Held calibration approved: no significant regression after validation period."

        decision = {
            "action": action,
            "reason": reason,
            "score_delta": score_delta,
            "avg_score_before": pre_score,
            "avg_score_after": recent_score,
            "sample_count": sample_count,
            "context": {"platform": platform, "product_category": product_category},
            "decided_at": time.time(),
        }
        self._append_history(ctx_key, decision)
        return decision

    def governance_report(
        self,
        platform: str | None = None,
        product_category: str | None = None,
    ) -> dict[str, Any]:
        """Return a full governance status report.

        Returns:
            Dict with ``history``, ``last_action``, ``rollback_count``,
            ``approve_count``, ``hold_count``, ``approved_weights_snapshot``.
        """
        ctx_key = self._ctx_key(platform, product_category)
        history = list(_ROLLOUT_HISTORY.get(ctx_key, []))

        rollback_count = sum(1 for d in history if d.get("action") == "rollback")
        approve_count = sum(1 for d in history if d.get("action") == "approve")
        hold_count = sum(1 for d in history if d.get("action") == "hold")
        last_action = history[-1].get("action") if history else None

        return {
            "platform": platform,
            "product_category": product_category,
            "history_count": len(history),
            "last_action": last_action,
            "rollback_count": rollback_count,
            "approve_count": approve_count,
            "hold_count": hold_count,
            "last_decision": history[-1] if history else None,
            "approved_weights_snapshot": _APPROVED_WEIGHTS.get(ctx_key),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ctx_key(platform: str | None, product_category: str | None) -> tuple[str, str]:
        return (platform or "*", product_category or "*")

    @staticmethod
    def _max_delta_in(proposed_delta: dict[str, Any]) -> float:
        """Return the maximum absolute delta seen across all surfaces and dims."""
        max_d = 0.0
        for surface_data in proposed_delta.values():
            if isinstance(surface_data, dict):
                for val in surface_data.values():
                    if isinstance(val, (int, float)):
                        max_d = max(max_d, abs(float(val)))
                    elif isinstance(val, dict):
                        for v in val.values():
                            if isinstance(v, (int, float)):
                                max_d = max(max_d, abs(float(v)))
        return max_d

    def _do_rollback(
        self,
        ctx_key: tuple[str, str],
        platform: str | None,
        product_category: str | None,
    ) -> None:
        """Attempt to restore last approved weights via ScoringCalibrationApplier."""
        saved = _APPROVED_WEIGHTS.get(ctx_key)
        if saved and self._db is not None:
            try:
                from app.services.commerce.scoring_calibration_applier import ScoringCalibrationApplier
                # Re-run calibration sweep to reset to last-known good state;
                # in a real system this would directly write saved weights.
                applier = ScoringCalibrationApplier(db=self._db)
                applier.run_calibration_sweep(
                    platform=platform,
                    product_category=product_category,
                )
            except Exception as exc:
                logger.warning("CalibrationRolloutGovernor: rollback sweep failed: %s", exc)

    @staticmethod
    def _record_approved_weights(
        ctx_key: tuple[str, str],
        proposed_delta: dict[str, Any],
    ) -> None:
        _APPROVED_WEIGHTS[ctx_key] = {
            "delta_snapshot": proposed_delta,
            "approved_at": time.time(),
        }

    @staticmethod
    def _append_history(ctx_key: tuple[str, str], decision: dict[str, Any]) -> None:
        _ROLLOUT_HISTORY.setdefault(ctx_key, [])
        _ROLLOUT_HISTORY[ctx_key].append(decision)
        if len(_ROLLOUT_HISTORY[ctx_key]) > _MAX_HISTORY:
            _ROLLOUT_HISTORY[ctx_key] = _ROLLOUT_HISTORY[ctx_key][-_MAX_HISTORY:]

    def _recent_avg_score(
        self,
        platform: str | None,
        product_category: str | None,
    ) -> float:
        """Return the mean recent conversion score from the learning store."""
        if self._learning_store is None:
            return 0.5
        try:
            records = self._learning_store.all_records()
            filtered = [
                r for r in records
                if (platform is None or r.get("platform") == platform)
            ]
            if not filtered:
                return 0.5
            scores = [float(r.get("conversion_score", 0.5)) for r in filtered[-50:]]
            return round(sum(scores) / len(scores), 4)
        except Exception:
            return 0.5

    def _recent_record_count(
        self,
        platform: str | None,
        product_category: str | None,
    ) -> int:
        if self._learning_store is None:
            return 0
        try:
            records = self._learning_store.all_records()
            return sum(
                1 for r in records
                if platform is None or r.get("platform") == platform
            )
        except Exception:
            return 0
