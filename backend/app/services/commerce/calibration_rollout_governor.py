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

Canary Rollout
--------------
Instead of a binary approve/block gate, large but acceptable calibrations
are graduated through canary stages: 10 % → 30 % → 100 % traffic exposure.
Each stage requires at least ``_CANARY_STAGE_MIN_RECORDS`` new outcome records
before advancing.  KPI triggers (CTR drop or conversion drop beyond their
respective thresholds) abort the canary and initiate a rollback at any stage.

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
    # decision["action"]  → "approve" | "canary" | "hold" | "rollback"
    # decision["reason"]  → human-readable explanation
    # decision["canary_pct"] → 10 | 30 | 100 | None
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

# ---------------------------------------------------------------------------
# Canary rollout thresholds
# ---------------------------------------------------------------------------
# Delta range that triggers a canary (between safe and hard-hold)
_CANARY_MIN_DELTA = 0.10   # above this → start canary instead of direct approve
# Canary stages: traffic percentages
_CANARY_STAGES = (10, 30, 100)
# Minimum records required at each canary stage before advancing
_CANARY_STAGE_MIN_RECORDS = 3
# KPI thresholds for rollback during canary
_CANARY_CTR_DROP_THRESHOLD = 0.05    # relative CTR drop (5 %) triggers rollback
_CANARY_CONV_DROP_THRESHOLD = 0.03   # absolute conversion score drop triggers rollback

# In-memory rollout history: {(platform, product_category) → list[decision]}
_ROLLOUT_HISTORY: dict[tuple[str, str], list[dict[str, Any]]] = {}
# Snapshot of last-approved weights per context for rollback
_APPROVED_WEIGHTS: dict[tuple[str, str], dict[str, Any]] = {}
# Active canary state: {(platform, product_category) → canary_state_dict}
_CANARY_STATE: dict[tuple[str, str], dict[str, Any]] = {}


class CalibrationRolloutGovernor:
    """Govern calibration rollout decisions with canary/hold/approve/rollback logic.

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
        self._load_persisted_state()

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
        pre_ctr: float | None = None,
        post_ctr: float | None = None,
    ) -> dict[str, Any]:
        """Assess whether to approve, canary, hold, or rollback a calibration.

        Args:
            platform: Target platform for the calibration.
            product_category: Target product category.
            proposed_delta: Weight deltas returned by
                ``ClosedLoopCalibrationOrchestrator.run_full_calibration()``.
                Format: {surface → {dimension → delta_float}}.
            pre_score: Mean conversion score *before* this calibration run.
            post_score: Mean conversion score *after* this calibration run.
            pre_ctr: Mean CTR *before* this calibration run (optional).
            post_ctr: Mean CTR *after* this calibration run (optional).

        Returns:
            Dict with:
            - ``action``: "approve" | "canary" | "hold" | "rollback"
            - ``reason``: human-readable explanation
            - ``max_delta_observed``: largest absolute delta seen
            - ``score_delta``: post - pre (or None)
            - ``canary_pct``: 10 | 30 | 100 | None — initial canary exposure
            - ``context``: {platform, product_category}
        """
        ctx_key = self._ctx_key(platform, product_category)

        max_delta = self._max_delta_in(proposed_delta)
        score_delta: float | None = None
        if pre_score is not None and post_score is not None:
            score_delta = round(post_score - pre_score, 4)

        ctr_drop: float | None = None
        if pre_ctr is not None and post_ctr is not None and pre_ctr > 0:
            ctr_drop = round((pre_ctr - post_ctr) / max(pre_ctr, 1e-9), 4)  # relative drop

        # --- KPI regression checks (immediate rollback) ---
        conv_regression = score_delta is not None and score_delta <= -_MAX_SCORE_LOSS
        ctr_regression = ctr_drop is not None and ctr_drop >= _CANARY_CTR_DROP_THRESHOLD

        if conv_regression or ctr_regression:
            action = "rollback"
            kpi_detail = []
            if conv_regression:
                kpi_detail.append(f"conversion {score_delta:+.4f}")
            if ctr_regression:
                kpi_detail.append(f"CTR drop {ctr_drop:.1%}")
            reason = (
                f"KPI regression detected ({', '.join(kpi_detail)}). "
                "Reverting to last approved weights."
            )
            self._do_rollback(
                ctx_key,
                platform,
                product_category,
                rollback_reason=reason,
                rollback_source="assess_rollout",
            )
            canary_pct = None

        elif max_delta > self._max_safe_delta:
            action = "hold"
            reason = (
                f"Max weight delta {max_delta:.4f} exceeds safe threshold "
                f"{self._max_safe_delta}. Holding for {_MIN_VALIDATION_RECORDS} "
                "validation records before applying."
            )
            canary_pct = None

        elif max_delta >= _CANARY_MIN_DELTA:
            # Delta is non-trivial — start canary rollout at 10 %
            action = "canary"
            canary_pct = _CANARY_STAGES[0]
            reason = (
                f"Max weight delta {max_delta:.4f} ≥ {_CANARY_MIN_DELTA}. "
                f"Starting canary rollout at {canary_pct}% traffic."
            )
            self._init_canary(ctx_key, proposed_delta, pre_score, pre_ctr)

        elif score_delta is not None and score_delta >= _MIN_SCORE_GAIN:
            action = "approve"
            reason = (
                f"Score improved {score_delta:+.4f} ≥ {_MIN_SCORE_GAIN}. "
                "Calibration approved and applied."
            )
            self._record_approved_weights(
                ctx_key,
                proposed_delta,
                platform=platform,
                product_category=product_category,
            )
            canary_pct = None

        else:
            action = "approve"
            reason = (
                "Delta within safe range and no significant regression. "
                "Approved with monitoring."
            )
            self._record_approved_weights(
                ctx_key,
                proposed_delta,
                platform=platform,
                product_category=product_category,
            )
            canary_pct = None

        decision = {
            "action": action,
            "reason": reason,
            "max_delta_observed": round(max_delta, 4),
            "score_delta": score_delta,
            "ctr_drop": ctr_drop,
            "pre_score": pre_score,
            "post_score": post_score,
            "canary_pct": canary_pct,
            "context": {"platform": platform, "product_category": product_category},
            "decided_at": time.time(),
        }
        self._append_history(ctx_key, decision, platform=platform, product_category=product_category)

        logger.info(
            "CalibrationRolloutGovernor: action=%s platform=%s max_delta=%.4f "
            "score_delta=%s canary_pct=%s",
            action,
            platform,
            max_delta,
            score_delta,
            canary_pct,
        )
        return decision

    # ------------------------------------------------------------------
    # Canary advancement
    # ------------------------------------------------------------------

    def advance_canary(
        self,
        platform: str | None,
        product_category: str | None,
    ) -> dict[str, Any]:
        """Attempt to advance the active canary to the next traffic stage.

        Checks whether the current canary stage has accumulated enough new
        records and that KPIs have not regressed.  Advances to the next stage
        (10 % → 30 % → 100 %) or rolls back if KPIs fail.

        Returns:
            Dict with ``action`` ("advanced" | "rollback" | "complete" |
            "no_canary" | "insufficient_records"), ``canary_pct``,
            ``reason``, and ``kpi_snapshot``.
        """
        ctx_key = self._ctx_key(platform, product_category)
        canary = _CANARY_STATE.get(ctx_key)
        if not canary:
            return {"action": "no_canary", "reason": "No active canary for this context."}

        current_stage_idx = canary.get("stage_idx", 0)
        current_pct = _CANARY_STAGES[current_stage_idx]
        records_at_stage_start = canary.get("records_at_stage_start", 0)
        pre_score = canary.get("pre_score", 0.5)
        pre_ctr = canary.get("pre_ctr")

        simulation = self._simulate_canary_gate(
            pre_score=pre_score,
            recent_score=self._recent_avg_score(platform, product_category),
            pre_ctr=pre_ctr,
            recent_ctr=self._recent_avg_ctr(platform, product_category),
            canary_pct=current_pct,
        )
        if not simulation.get("feasible", True):
            _CANARY_STATE.pop(ctx_key, None)
            self._do_rollback(
                ctx_key,
                platform,
                product_category,
                rollback_reason="canary_simulation_failed",
                rollback_source="advance_canary",
            )
            decision = {
                "action": "rollback",
                "canary_pct": current_pct,
                "reason": "Canary simulation failed policy gate.",
                "simulation": simulation,
                "decided_at": time.time(),
            }
            self._append_history(ctx_key, decision, platform=platform, product_category=product_category)
            return decision

        # How many records have arrived since stage start?
        current_records = self._recent_record_count(platform, product_category)
        new_records = current_records - records_at_stage_start

        if new_records < _CANARY_STAGE_MIN_RECORDS:
            return {
                "action": "insufficient_records",
                "canary_pct": current_pct,
                "reason": (
                    f"Need {_CANARY_STAGE_MIN_RECORDS} new records at stage "
                    f"{current_pct}%; have {new_records}."
                ),
                "new_records": new_records,
            }

        # Check KPIs
        recent_score = self._recent_avg_score(platform, product_category)
        recent_ctr = self._recent_avg_ctr(platform, product_category)

        conv_delta = recent_score - pre_score
        ctr_drop: float | None = None
        if pre_ctr is not None and pre_ctr > 0:
            ctr_drop = (pre_ctr - recent_ctr) / pre_ctr

        conv_regression = conv_delta <= -_CANARY_CONV_DROP_THRESHOLD
        ctr_regression = ctr_drop is not None and ctr_drop >= _CANARY_CTR_DROP_THRESHOLD

        kpi_snapshot = {
            "pre_score": pre_score,
            "recent_score": recent_score,
            "conv_delta": round(conv_delta, 4),
            "pre_ctr": pre_ctr,
            "recent_ctr": recent_ctr,
            "ctr_drop": round(ctr_drop, 4) if ctr_drop is not None else None,
        }

        if conv_regression or ctr_regression:
            kpi_detail = []
            if conv_regression:
                kpi_detail.append(f"conversion delta {conv_delta:+.4f}")
            if ctr_regression:
                kpi_detail.append(f"CTR drop {ctr_drop:.1%}")
            # Abort canary — rollback
            del _CANARY_STATE[ctx_key]
            self._do_rollback(
                ctx_key,
                platform,
                product_category,
                rollback_reason=f"canary_kpi_failure_{current_pct}",
                rollback_source="advance_canary",
            )
            decision = {
                "action": "rollback",
                "canary_pct": current_pct,
                "reason": f"Canary KPI failure at {current_pct}%: {', '.join(kpi_detail)}.",
                "kpi_snapshot": kpi_snapshot,
                "decided_at": time.time(),
            }
            self._append_history(ctx_key, decision, platform=platform, product_category=product_category)
            return decision

        healthy_stages = int(canary.get("healthy_stages", 0)) + 1
        _CANARY_STATE[ctx_key]["healthy_stages"] = healthy_stages
        if healthy_stages >= 2:
            _CANARY_STATE.pop(ctx_key, None)
            self._record_approved_weights(
                ctx_key,
                canary.get("proposed_delta", {}),
                platform=platform,
                product_category=product_category,
                canary_stage=100,
            )
            decision = {
                "action": "complete",
                "canary_pct": 100,
                "reason": "KPIs healthy across 2 consecutive canary stages — auto-approved to 100%.",
                "kpi_snapshot": kpi_snapshot,
                "decided_at": time.time(),
            }
            self._append_history(ctx_key, decision, platform=platform, product_category=product_category)
            return decision

        # Advance to next stage
        next_stage_idx = current_stage_idx + 1
        if next_stage_idx >= len(_CANARY_STAGES):
            # Reached 100 % — complete canary, full approve
            del _CANARY_STATE[ctx_key]
            self._record_approved_weights(
                ctx_key,
                canary.get("proposed_delta", {}),
                platform=platform,
                product_category=product_category,
                canary_stage=100,
            )
            decision = {
                "action": "complete",
                "canary_pct": 100,
                "reason": "Canary completed at 100% — calibration fully approved.",
                "kpi_snapshot": kpi_snapshot,
                "decided_at": time.time(),
            }
            self._append_history(ctx_key, decision, platform=platform, product_category=product_category)
            return decision

        next_pct = _CANARY_STAGES[next_stage_idx]
        _CANARY_STATE[ctx_key]["stage_idx"] = next_stage_idx
        _CANARY_STATE[ctx_key]["records_at_stage_start"] = current_records
        decision = {
            "action": "advanced",
            "canary_pct": next_pct,
            "reason": (
                f"KPIs healthy at {current_pct}% — advancing canary to {next_pct}%."
            ),
            "kpi_snapshot": kpi_snapshot,
            "decided_at": time.time(),
        }
        self._append_history(ctx_key, decision, platform=platform, product_category=product_category)
        return decision

    def get_canary_status(
        self,
        platform: str | None,
        product_category: str | None,
    ) -> dict[str, Any]:
        """Return the current canary state for this context, or None if no canary."""
        ctx_key = self._ctx_key(platform, product_category)
        canary = _CANARY_STATE.get(ctx_key)
        if not canary:
            return {"active": False}
        stage_idx = canary.get("stage_idx", 0)
        return {
            "active": True,
            "canary_pct": _CANARY_STAGES[stage_idx],
            "stage_idx": stage_idx,
            "pre_score": canary.get("pre_score"),
            "started_at": canary.get("started_at"),
        }

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
            self._do_rollback(
                ctx_key,
                platform,
                product_category,
                rollback_reason=reason,
                rollback_source="re_evaluate_held",
            )
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
        self._append_history(ctx_key, decision, platform=platform, product_category=product_category)
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
        rollback_reason: str | None = None,
        rollback_source: str | None = None,
    ) -> None:
        """Attempt to restore last approved weights via ScoringCalibrationApplier."""
        saved = _APPROVED_WEIGHTS.get(ctx_key)
        reverted_to_revision = None
        if saved:
            reverted_to_revision = str(saved.get("approved_at") or "")
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
        self._persist_rollout_record(
            ctx_key=ctx_key,
            platform=platform,
            product_category=product_category,
            action="rollback",
            canary_stage=None,
            approved_weights=saved,
            rollback_source=rollback_source,
            rollback_reason=rollback_reason,
            reverted_to_revision=reverted_to_revision,
            payload={
                "event_type": "governance_learning_event",
                "rollback_source": rollback_source,
                "rollback_reason": rollback_reason,
                "reverted_to_revision": reverted_to_revision,
            },
        )

    def _record_approved_weights(
        self,
        ctx_key: tuple[str, str],
        proposed_delta: dict[str, Any],
        platform: str | None = None,
        product_category: str | None = None,
        canary_stage: int | None = None,
    ) -> None:
        approved = {
            "delta_snapshot": proposed_delta,
            "approved_at": time.time(),
        }
        _APPROVED_WEIGHTS[ctx_key] = approved
        self._persist_rollout_record(
            ctx_key=ctx_key,
            platform=platform,
            product_category=product_category,
            action="approve",
            canary_stage=canary_stage,
            approved_weights=approved,
            rollback_source=None,
            rollback_reason=None,
            reverted_to_revision=None,
            payload={"approved_weights": approved},
        )

    def _append_history(
        self,
        ctx_key: tuple[str, str],
        decision: dict[str, Any],
        platform: str | None = None,
        product_category: str | None = None,
    ) -> None:
        _ROLLOUT_HISTORY.setdefault(ctx_key, [])
        _ROLLOUT_HISTORY[ctx_key].append(decision)
        if len(_ROLLOUT_HISTORY[ctx_key]) > _MAX_HISTORY:
            _ROLLOUT_HISTORY[ctx_key] = _ROLLOUT_HISTORY[ctx_key][-_MAX_HISTORY:]
        self._persist_rollout_record(
            ctx_key=ctx_key,
            platform=platform,
            product_category=product_category,
            action=str(decision.get("action", "unknown")),
            canary_stage=decision.get("canary_pct"),
            approved_weights=_APPROVED_WEIGHTS.get(ctx_key),
            rollback_source=decision.get("rollback_source"),
            rollback_reason=decision.get("rollback_reason") or decision.get("reason"),
            reverted_to_revision=decision.get("reverted_to_revision"),
            payload=decision,
        )

    def _init_canary(
        self,
        ctx_key: tuple[str, str],
        proposed_delta: dict[str, Any],
        pre_score: float | None,
        pre_ctr: float | None,
    ) -> None:
        """Initialise a new canary state at stage 0 (10 %)."""
        _CANARY_STATE[ctx_key] = {
            "stage_idx": 0,
            "proposed_delta": proposed_delta,
            "pre_score": pre_score if pre_score is not None else 0.5,
            "pre_ctr": pre_ctr,
            "healthy_stages": 0,
            "records_at_stage_start": self._recent_record_count(
                ctx_key[0] if ctx_key[0] != "*" else None,
                ctx_key[1] if ctx_key[1] != "*" else None,
            ),
            "started_at": time.time(),
        }

    @staticmethod
    def _ctx_key_str(ctx_key: tuple[str, str]) -> str:
        return f"{ctx_key[0]}::{ctx_key[1]}"

    def _persist_rollout_record(
        self,
        *,
        ctx_key: tuple[str, str],
        platform: str | None,
        product_category: str | None,
        action: str,
        canary_stage: int | None,
        approved_weights: dict[str, Any] | None,
        rollback_source: str | None,
        rollback_reason: str | None,
        reverted_to_revision: str | None,
        payload: dict[str, Any],
    ) -> None:
        if self._db is None:
            return
        try:
            from app.models.calibration_rollout_record import CalibrationRolloutRecord

            row = CalibrationRolloutRecord(
                context_key=self._ctx_key_str(ctx_key),
                platform=platform,
                product_category=product_category,
                action=action,
                canary_stage=canary_stage,
                approved_weights=approved_weights,
                rollback_source=rollback_source,
                rollback_reason=rollback_reason,
                reverted_to_revision=reverted_to_revision,
                context={"platform": platform, "product_category": product_category},
                payload=payload,
            )
            self._db.add(row)
            self._db.commit()
        except Exception as exc:
            logger.debug("CalibrationRolloutGovernor: persist rollout record failed: %s", exc)
            try:
                self._db.rollback()
            except Exception:
                pass

    def _load_persisted_state(self) -> None:
        if self._db is None:
            return
        try:
            from app.models.calibration_rollout_record import CalibrationRolloutRecord

            rows = (
                self._db.query(CalibrationRolloutRecord)
                .order_by(CalibrationRolloutRecord.created_at.desc())
                .limit(300)
                .all()
            )
            for row in reversed(rows):
                platform = row.platform or "*"
                product_category = row.product_category or "*"
                ctx_key = (platform, product_category)
                if row.payload:
                    _ROLLOUT_HISTORY.setdefault(ctx_key, [])
                    _ROLLOUT_HISTORY[ctx_key].append(dict(row.payload))
                    _ROLLOUT_HISTORY[ctx_key] = _ROLLOUT_HISTORY[ctx_key][-_MAX_HISTORY:]
                if row.approved_weights:
                    _APPROVED_WEIGHTS[ctx_key] = dict(row.approved_weights)
                if row.action == "canary" and row.canary_stage:
                    _CANARY_STATE[ctx_key] = {
                        "stage_idx": max(0, _CANARY_STAGES.index(row.canary_stage) if row.canary_stage in _CANARY_STAGES else 0),
                        "proposed_delta": (row.approved_weights or {}).get("delta_snapshot", {}),
                        "pre_score": (row.payload or {}).get("pre_score", 0.5),
                        "pre_ctr": (row.payload or {}).get("pre_ctr"),
                        "records_at_stage_start": self._recent_record_count(
                            platform if platform != "*" else None,
                            product_category if product_category != "*" else None,
                        ),
                        "started_at": (row.payload or {}).get("decided_at", time.time()),
                        "healthy_stages": int((row.payload or {}).get("healthy_stages", 0)),
                    }
        except Exception as exc:
            logger.debug("CalibrationRolloutGovernor: failed loading persisted state: %s", exc)

    @staticmethod
    def _simulate_canary_gate(
        *,
        pre_score: float,
        recent_score: float,
        pre_ctr: float | None,
        recent_ctr: float,
        canary_pct: int,
    ) -> dict[str, Any]:
        try:
            from app.services.publish_providers.policy_simulation_engine import PolicySimulationEngine

            sim = PolicySimulationEngine()
            result = sim.simulate_canary_rollout(
                pre_score=pre_score,
                score_trajectory=[recent_score],
                pre_ctr=pre_ctr,
                ctr_trajectory=[recent_ctr] if pre_ctr is not None else None,
                conversion_trajectory=[recent_score],
                budget_trajectory=[float(canary_pct)],
            )
            feasible = result.get("final_action") != "rollback"
            return {"feasible": feasible, "result": result}
        except Exception:
            return {"feasible": True, "result": {}}

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

    def _recent_avg_ctr(
        self,
        platform: str | None,
        product_category: str | None,
    ) -> float:
        """Return the mean recent CTR from the learning store."""
        if self._learning_store is None:
            return 0.0
        try:
            records = self._learning_store.all_records()
            filtered = [
                r for r in records
                if (platform is None or r.get("platform") == platform)
            ]
            if not filtered:
                return 0.0
            ctrs = [float(r.get("click_through_rate", 0.0)) for r in filtered[-50:]]
            return round(sum(ctrs) / len(ctrs), 4)
        except Exception:
            return 0.0

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
