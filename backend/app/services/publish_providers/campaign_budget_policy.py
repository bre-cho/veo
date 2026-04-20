"""CampaignBudgetPolicy — per-campaign and per-platform daily publish limits.

Prevents a single channel plan or platform from flooding the publish queue
beyond configured thresholds.  The policy is evaluated in
``PublishScheduler.run_job()`` before any actual provider call is made.

Configuration (all via environment variables):
    CAMPAIGN_DAILY_PUBLISH_LIMIT   Max publishes per channel_plan_id per day.
                                   Default: 5.
    PLATFORM_DAILY_PUBLISH_LIMIT   Max publishes per platform per day across
                                   all channel plans.  Default: 20.

Both limits are enforced independently; exceeding either raises
``BudgetExceededError``.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.models.publish_job import PublishJob

logger = logging.getLogger(__name__)

_CAMPAIGN_DAILY_LIMIT = int(os.environ.get("CAMPAIGN_DAILY_PUBLISH_LIMIT", "5"))
_PLATFORM_DAILY_LIMIT = int(os.environ.get("PLATFORM_DAILY_PUBLISH_LIMIT", "20"))


class BudgetExceededError(RuntimeError):
    """Raised when a publish job would exceed a campaign or platform budget."""

    def __init__(self, reason: str, detail: dict[str, Any]) -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(f"Publish budget exceeded: {reason} — {detail}")


class CampaignBudgetPolicy:
    """Enforce per-campaign and per-platform daily publish limits.

    Usage::

        policy = CampaignBudgetPolicy()
        policy.check(db, job)   # raises BudgetExceededError when limit exceeded

    ``check_status()`` returns a read-only dict without raising, useful for
    monitoring and dashboards.
    """

    def __init__(
        self,
        campaign_daily_limit: int = _CAMPAIGN_DAILY_LIMIT,
        platform_daily_limit: int = _PLATFORM_DAILY_LIMIT,
    ) -> None:
        self.campaign_daily_limit = campaign_daily_limit
        self.platform_daily_limit = platform_daily_limit

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, db: "Session", job: "PublishJob") -> None:
        """Assert that running ``job`` will not exceed any budget.

        Raises ``BudgetExceededError`` when the campaign or platform daily
        limit would be exceeded.  Limits are computed by counting published
        (``status='published'``) jobs within the current calendar day (UTC).
        """
        today_start = _today_utc()

        if job.channel_plan_id:
            campaign_count = self._count_today(
                db,
                today_start,
                channel_plan_id=job.channel_plan_id,
            )
            if campaign_count >= self.campaign_daily_limit:
                detail = {
                    "channel_plan_id": job.channel_plan_id,
                    "published_today": campaign_count,
                    "limit": self.campaign_daily_limit,
                }
                logger.warning(
                    "CampaignBudgetPolicy: campaign limit reached channel_plan_id=%s "
                    "published=%d limit=%d",
                    job.channel_plan_id,
                    campaign_count,
                    self.campaign_daily_limit,
                )
                raise BudgetExceededError("campaign_daily_limit", detail)

        platform_count = self._count_today(db, today_start, platform=job.platform)
        if platform_count >= self.platform_daily_limit:
            detail = {
                "platform": job.platform,
                "published_today": platform_count,
                "limit": self.platform_daily_limit,
            }
            logger.warning(
                "CampaignBudgetPolicy: platform limit reached platform=%s "
                "published=%d limit=%d",
                job.platform,
                platform_count,
                self.platform_daily_limit,
            )
            raise BudgetExceededError("platform_daily_limit", detail)

    def check_status(
        self,
        db: "Session",
        channel_plan_id: str | None = None,
        platform: str | None = None,
    ) -> dict[str, Any]:
        """Return remaining budget for the current day without raising.

        Useful for monitoring endpoints and pre-scheduling capacity checks.
        """
        today_start = _today_utc()
        result: dict[str, Any] = {
            "date_utc": today_start.date().isoformat(),
        }

        if channel_plan_id:
            count = self._count_today(db, today_start, channel_plan_id=channel_plan_id)
            result["campaign"] = {
                "channel_plan_id": channel_plan_id,
                "published_today": count,
                "limit": self.campaign_daily_limit,
                "remaining": max(0, self.campaign_daily_limit - count),
                "ok": count < self.campaign_daily_limit,
            }

        if platform:
            count = self._count_today(db, today_start, platform=platform)
            result["platform"] = {
                "platform": platform,
                "published_today": count,
                "limit": self.platform_daily_limit,
                "remaining": max(0, self.platform_daily_limit - count),
                "ok": count < self.platform_daily_limit,
            }

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _count_today(
        db: "Session",
        today_start: datetime,
        *,
        channel_plan_id: str | None = None,
        platform: str | None = None,
    ) -> int:
        """Count published jobs since ``today_start``."""
        try:
            from app.models.publish_job import PublishJob

            query = db.query(PublishJob).filter(
                PublishJob.status == "published",
                PublishJob.published_at >= today_start,
            )
            if channel_plan_id is not None:
                query = query.filter(PublishJob.channel_plan_id == channel_plan_id)
            if platform is not None:
                query = query.filter(PublishJob.platform == platform)
            return query.count()
        except Exception:
            # Fail open: if we cannot query, don't block the publish
            return 0


def _today_utc() -> datetime:
    """Return the start of the current UTC calendar day."""
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)


# ---------------------------------------------------------------------------
# Phase 1.4 / 3.4: Portfolio-level budget orchestration
# ---------------------------------------------------------------------------


class CampaignBudget:
    """Simple data class representing a campaign's budget info."""

    def __init__(
        self,
        campaign_id: str,
        daily_limit: float,
        roas: float = 1.0,
        remaining: float | None = None,
    ) -> None:
        self.campaign_id = campaign_id
        self.daily_limit = daily_limit
        self.roas = max(0.0, roas)
        # remaining defaults to daily_limit if not specified
        self.remaining = remaining if remaining is not None else daily_limit


class PortfolioBudgetOrchestrator:
    """Allocate a total budget across a portfolio of campaigns.

    ``allocate()`` distributes ``total_remaining`` slots/budget across
    campaigns using ROAS-weighted proportional allocation.  Campaigns that
    have already reached their ``daily_limit`` are excluded.

    Usage::

        orchestrator = PortfolioBudgetOrchestrator()
        allocation = orchestrator.allocate(campaigns, total_remaining=100)
        # Returns {campaign_id -> slots_allocated}
    """

    def allocate(
        self,
        portfolio: list[CampaignBudget],
        total_remaining: float,
    ) -> dict[str, float]:
        """Distribute ``total_remaining`` across eligible campaigns by ROAS weight.

        Args:
            portfolio: List of ``CampaignBudget`` objects.
            total_remaining: Total budget/slots to distribute.

        Returns:
            Dict mapping campaign_id → allocated amount.  The sum of all
            values is ≤ ``total_remaining``.  Campaigns that have reached
            their ``daily_limit`` receive 0.
        """
        if total_remaining <= 0 or not portfolio:
            return {c.campaign_id: 0.0 for c in portfolio}

        # Eligible campaigns: those with remaining headroom
        eligible = [c for c in portfolio if c.remaining > 0]
        if not eligible:
            return {c.campaign_id: 0.0 for c in portfolio}

        # ROAS-weighted proportional allocation
        total_roas = sum(c.roas for c in eligible)
        if total_roas <= 0:
            # Fallback: equal distribution
            equal_share = total_remaining / len(eligible)
            weights = {c.campaign_id: equal_share for c in eligible}
        else:
            weights = {
                c.campaign_id: (c.roas / total_roas) * total_remaining
                for c in eligible
            }

        allocation: dict[str, float] = {}
        allocated_total = 0.0
        for campaign in portfolio:
            if campaign.remaining <= 0:
                allocation[campaign.campaign_id] = 0.0
                continue
            # Cap at campaign's remaining headroom
            alloc = min(weights.get(campaign.campaign_id, 0.0), campaign.remaining)
            alloc = round(alloc, 4)
            allocation[campaign.campaign_id] = alloc
            allocated_total += alloc

        # Safety: ensure total allocation ≤ total_remaining due to rounding
        if allocated_total > total_remaining:
            # Scale down proportionally
            scale = total_remaining / allocated_total
            allocation = {
                k: round(v * scale, 4) for k, v in allocation.items()
            }

        return allocation

    def allocate_budget_across_campaigns(
        self,
        campaigns: list[dict[str, Any]],
        total_budget: float,
        performance_model: Any | None = None,
    ) -> dict[str, float]:
        """Allocate ``total_budget`` (Phase 1.4 API) across campaign dicts.

        Each campaign dict should have keys: ``campaign_id``, ``daily_limit``,
        and optionally ``roas``.  When ``performance_model`` is provided,
        ROAS is derived from its records for the campaign.

        Returns ``{campaign_id → daily_limit}`` allocation.
        """
        portfolio: list[CampaignBudget] = []
        for c in campaigns:
            cid = c.get("campaign_id", "")
            daily_limit = float(c.get("daily_limit", total_budget))
            # Try to get ROAS from performance model
            roas = float(c.get("roas", 1.0))
            if performance_model is not None:
                try:
                    records = performance_model.all_records()
                    campaign_records = [r for r in records if r.get("campaign_id") == cid]
                    if campaign_records:
                        metrics_roas = [
                            float((r.get("performance_metrics") or {}).get("roas", 1.0))
                            for r in campaign_records
                        ]
                        roas = sum(metrics_roas) / len(metrics_roas)
                except Exception:
                    pass
            portfolio.append(CampaignBudget(campaign_id=cid, daily_limit=daily_limit, roas=roas))
        return self.allocate(portfolio, total_budget)

