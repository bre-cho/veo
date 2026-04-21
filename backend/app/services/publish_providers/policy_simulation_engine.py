"""PolicySimulationEngine — simulate quota, budget, and rollout policies before deploy.

Provides a safe simulation layer for testing publish policy decisions without
actually touching platform APIs or consuming real quota.  Run simulations
*before* deploying a new campaign batch to identify quota overruns, budget
exhaustion, and compliance blocks before they cause live failures.

Capabilities
------------
- **Quota simulation**: projects whether a campaign batch will stay within
  daily/hourly quota limits across all platforms.
- **Budget simulation**: forecasts spend against daily budget caps for each
  campaign over a configurable horizon.
- **Rollout simulation**: models canary rollout stages for a calibration,
  predicting whether KPI thresholds will hold at each stage.
- **Dry-run publish**: validates a batch of publish jobs through the full
  compliance + quota stack without dispatching.

Usage::

    sim = PolicySimulationEngine()

    # Check quota before a batch publish:
    result = sim.simulate_quota(
        jobs=[{"campaign_id": "c1", "platform": "tiktok"}, ...],
        current_quota_state={"c1": {"daily_publish_count": 3}},
    )
    # result["feasible"] → bool
    # result["violations"] → list of quota violations

    # Simulate a 3-stage canary rollout:
    canary = sim.simulate_canary_rollout(
        pre_score=0.52,
        score_trajectory=[0.54, 0.56, 0.58],
        pre_ctr=0.05,
        ctr_trajectory=[0.049, 0.051, 0.053],
    )
    # canary["stages"] → list of {stage_pct, action, kpi_ok}
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Mirrors constants from CalibrationRolloutGovernor and PortfolioQuotaOrchestrator
_DEFAULT_DAILY_PUBLISH_LIMIT = 5
_DEFAULT_HOURLY_RATE_LIMIT = 3
_DEFAULT_DAILY_SPEND_LIMIT = 100.0
_CANARY_STAGES = (10, 30, 100)
_CANARY_CTR_DROP_THRESHOLD = 0.05
_CANARY_CONV_DROP_THRESHOLD = 0.03


class PolicySimulationEngine:
    """Simulate publish policies before deploying to production."""

    # ------------------------------------------------------------------
    # Quota simulation
    # ------------------------------------------------------------------

    def simulate_quota(
        self,
        jobs: list[dict[str, Any]],
        current_quota_state: dict[str, dict[str, Any]] | None = None,
        daily_publish_limit: int = _DEFAULT_DAILY_PUBLISH_LIMIT,
        hourly_rate_limit: int = _DEFAULT_HOURLY_RATE_LIMIT,
        platform_limits: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Simulate whether a set of publish jobs will stay within quota limits.

        Args:
            jobs: List of job dicts with at minimum ``campaign_id`` and
                ``platform``.
            current_quota_state: Existing quota counters keyed by
                ``campaign_id``.  Each entry is a dict with optional keys
                ``daily_publish_count``, ``hourly_count``.
            daily_publish_limit: Default per-campaign daily publish limit.
            hourly_rate_limit: Default per-campaign hourly rate limit.
            platform_limits: Override per-platform daily limits
                (e.g. ``{"tiktok": 3, "youtube": 1}``).

        Returns:
            Dict with:
            - ``feasible``: bool — True if all jobs fit within quota.
            - ``violations``: list of violation dicts.
            - ``projected_counts``: {campaign_id: {daily, hourly}} after batch.
            - ``jobs_checked``: int
        """
        quota: dict[str, dict[str, int]] = {}
        for cid, state in (current_quota_state or {}).items():
            quota[cid] = {
                "daily": int(state.get("daily_publish_count", 0)),
                "hourly": int(state.get("hourly_count", 0)),
            }

        violations: list[dict[str, Any]] = []

        for job in jobs:
            cid = str(job.get("campaign_id", "unknown"))
            platform = str(job.get("platform", "unknown")).lower()

            quota.setdefault(cid, {"daily": 0, "hourly": 0})
            quota[cid]["daily"] += 1
            quota[cid]["hourly"] += 1

            # Check daily campaign limit
            eff_daily = daily_publish_limit
            if platform_limits and platform in platform_limits:
                eff_daily = min(eff_daily, platform_limits[platform])

            if quota[cid]["daily"] > eff_daily:
                violations.append({
                    "campaign_id": cid,
                    "platform": platform,
                    "violation_type": "daily_publish_limit",
                    "current": quota[cid]["daily"],
                    "limit": eff_daily,
                })

            if quota[cid]["hourly"] > hourly_rate_limit:
                violations.append({
                    "campaign_id": cid,
                    "platform": platform,
                    "violation_type": "hourly_rate_limit",
                    "current": quota[cid]["hourly"],
                    "limit": hourly_rate_limit,
                })

        return {
            "feasible": len(violations) == 0,
            "violations": violations,
            "projected_counts": {
                cid: {"daily": v["daily"], "hourly": v["hourly"]}
                for cid, v in quota.items()
            },
            "jobs_checked": len(jobs),
        }

    # ------------------------------------------------------------------
    # Budget simulation
    # ------------------------------------------------------------------

    def simulate_budget(
        self,
        campaign_spend_plan: list[dict[str, Any]],
        daily_spend_limit: float = _DEFAULT_DAILY_SPEND_LIMIT,
        horizon_days: int = 7,
    ) -> dict[str, Any]:
        """Forecast spend against budget caps over a multi-day horizon.

        Args:
            campaign_spend_plan: List of dicts with ``campaign_id``,
                ``daily_spend`` (projected spend per day), and optionally
                ``budget_limit``.
            daily_spend_limit: Default portfolio daily spend cap.
            horizon_days: Number of days to project.

        Returns:
            Dict with:
            - ``feasible``: bool — True if no campaign exceeds its budget.
            - ``violations``: list of budget violations.
            - ``spend_projections``: {campaign_id: {day_N: projected_total}}.
        """
        violations: list[dict[str, Any]] = []
        projections: dict[str, dict[str, float]] = {}

        for camp in campaign_spend_plan:
            cid = str(camp.get("campaign_id", "unknown"))
            daily = float(camp.get("daily_spend", 0.0))
            limit = float(camp.get("budget_limit", daily_spend_limit))
            proj: dict[str, float] = {}
            cumulative = 0.0
            for day in range(1, horizon_days + 1):
                cumulative += daily
                proj[f"day_{day}"] = round(cumulative, 2)
                if cumulative > limit:
                    violations.append({
                        "campaign_id": cid,
                        "violation_type": "budget_exceeded",
                        "day": day,
                        "cumulative_spend": round(cumulative, 2),
                        "limit": limit,
                    })
                    break
            projections[cid] = proj

        return {
            "feasible": len(violations) == 0,
            "violations": violations,
            "spend_projections": projections,
            "horizon_days": horizon_days,
            "campaigns_checked": len(campaign_spend_plan),
        }

    # ------------------------------------------------------------------
    # Canary rollout simulation
    # ------------------------------------------------------------------

    def simulate_canary_rollout(
        self,
        pre_score: float,
        score_trajectory: list[float],
        pre_ctr: float | None = None,
        ctr_trajectory: list[float] | None = None,
    ) -> dict[str, Any]:
        """Simulate a 3-stage canary rollout (10% → 30% → 100%) against KPI trajectories.

        Each element in ``score_trajectory`` / ``ctr_trajectory`` represents the
        projected metric value at that canary stage.  The simulation applies the
        same KPI thresholds as ``CalibrationRolloutGovernor.advance_canary()``.

        Args:
            pre_score: Baseline conversion score before rollout.
            score_trajectory: Projected conversion scores at each canary stage
                (len 3: stage 10%, 30%, 100%).
            pre_ctr: Baseline CTR before rollout (optional).
            ctr_trajectory: Projected CTR values at each canary stage (optional).

        Returns:
            Dict with:
            - ``stages``: list of {stage_pct, conversion_delta, ctr_drop, action, kpi_ok}
            - ``final_action``: "complete" | "rollback" — overall simulation outcome
            - ``rollback_at_stage``: pct where rollback would occur, or None
        """
        stages: list[dict[str, Any]] = []
        rollback_at: int | None = None

        for i, stage_pct in enumerate(_CANARY_STAGES):
            score_at = score_trajectory[i] if i < len(score_trajectory) else pre_score
            conv_delta = score_at - pre_score

            ctr_drop: float | None = None
            if pre_ctr and ctr_trajectory and i < len(ctr_trajectory):
                ctr_at = ctr_trajectory[i]
                ctr_drop = (pre_ctr - ctr_at) / max(pre_ctr, 1e-9)

            conv_fail = conv_delta <= -_CANARY_CONV_DROP_THRESHOLD
            ctr_fail = ctr_drop is not None and ctr_drop >= _CANARY_CTR_DROP_THRESHOLD
            kpi_ok = not (conv_fail or ctr_fail)

            if not kpi_ok and rollback_at is None:
                action = "rollback"
                rollback_at = stage_pct
            elif i == len(_CANARY_STAGES) - 1 and kpi_ok:
                action = "complete"
            elif kpi_ok:
                action = "advance"
            else:
                action = "rollback"

            stages.append({
                "stage_pct": stage_pct,
                "projected_conversion_score": round(score_at, 4),
                "conversion_delta": round(conv_delta, 4),
                "projected_ctr_drop": round(ctr_drop, 4) if ctr_drop is not None else None,
                "kpi_ok": kpi_ok,
                "action": action,
            })

            if rollback_at is not None:
                break

        final_action = "complete" if rollback_at is None else "rollback"
        return {
            "stages": stages,
            "final_action": final_action,
            "rollback_at_stage_pct": rollback_at,
            "pre_score": pre_score,
            "pre_ctr": pre_ctr,
        }

    # ------------------------------------------------------------------
    # Dry-run publish
    # ------------------------------------------------------------------

    def dry_run_publish(
        self,
        jobs: list[dict[str, Any]],
        region_code: str = "US",
        current_quota_state: dict[str, dict[str, Any]] | None = None,
        daily_publish_limit: int = _DEFAULT_DAILY_PUBLISH_LIMIT,
    ) -> dict[str, Any]:
        """Validate a publish batch through quota + compliance without dispatching.

        Combines quota simulation and a lightweight compliance keyword check.

        Args:
            jobs: List of job dicts with ``campaign_id``, ``platform``,
                and optionally ``title``, ``description``, ``tags``.
            region_code: Region for compliance check.
            current_quota_state: Existing quota counters.
            daily_publish_limit: Per-campaign daily publish limit.

        Returns:
            Dict with:
            - ``all_clear``: bool — True if no quota or compliance violations.
            - ``quota_result``: result of ``simulate_quota()``.
            - ``compliance_checks``: list of per-job compliance notes.
            - ``blocked_jobs``: list of job indices that would be blocked.
        """
        quota_result = self.simulate_quota(
            jobs=jobs,
            current_quota_state=current_quota_state,
            daily_publish_limit=daily_publish_limit,
        )

        compliance_checks: list[dict[str, Any]] = []
        blocked_jobs: list[int] = []

        for idx, job in enumerate(jobs):
            title = str(job.get("title", "")).lower()
            description = str(job.get("description", "")).lower()
            tags = [str(t).lower() for t in job.get("tags", [])]
            content = f"{title} {description} {' '.join(tags)}"

            issues: list[str] = []
            # Basic adult/sensitive keyword check
            _SENSITIVE = ("adult", "explicit", "18+", "nsfw", "nude", "gambling", "cannabis")
            if any(kw in content for kw in _SENSITIVE):
                issues.append("sensitive_content_keyword")

            # Platform-specific title length check
            platform = str(job.get("platform", "")).lower()
            if platform in ("youtube", "shorts") and len(title) > 100:
                issues.append("title_too_long_youtube")
            elif platform == "tiktok" and len(title) > 150:
                issues.append("title_too_long_tiktok")

            if issues:
                blocked_jobs.append(idx)

            compliance_checks.append({
                "job_index": idx,
                "campaign_id": job.get("campaign_id"),
                "platform": job.get("platform"),
                "issues": issues,
                "clear": len(issues) == 0,
            })

        all_clear = quota_result["feasible"] and len(blocked_jobs) == 0
        logger.info(
            "PolicySimulationEngine.dry_run_publish: %d jobs all_clear=%s "
            "quota_violations=%d compliance_blocks=%d",
            len(jobs),
            all_clear,
            len(quota_result["violations"]),
            len(blocked_jobs),
        )
        return {
            "all_clear": all_clear,
            "quota_result": quota_result,
            "compliance_checks": compliance_checks,
            "blocked_jobs": blocked_jobs,
            "jobs_checked": len(jobs),
        }
