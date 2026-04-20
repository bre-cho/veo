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
