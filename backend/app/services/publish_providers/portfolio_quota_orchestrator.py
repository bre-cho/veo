"""PortfolioQuotaOrchestrator — multi-dimensional portfolio-level quota management.

Phase 3.5 (v16): Extends the existing ``PortfolioBudgetOrchestrator``
(ROAS-weighted allocation) with multi-dimensional quota tracking:

Dimensions tracked per campaign:
    - daily_spend: actual spend accumulated today
    - daily_publish_count: publishes executed today
    - hourly_rate: publishes in the current hour (rate limiting)
    - overage_count: number of times daily_limit was exceeded
    - platform_quota: per-platform remaining capacity

Capabilities:
    - ``check_quota()``: atomic multi-dimension gate before each publish.
    - ``record_publish()``: update all quota counters after a publish.
    - ``rebalance_portfolio()``: redistribute remaining capacity when some
      campaigns have excess and others are under-budget.
    - ``overage_alert_summary()``: surface campaigns near or at overage.
    - ``quota_dashboard()``: full portfolio quota status snapshot.

Usage::

    orchestrator = PortfolioQuotaOrchestrator()

    # Before publish:
    check = orchestrator.check_quota(
        campaign_id="camp-001",
        platform="tiktok",
        spend_amount=0.5,
    )
    if check["allowed"]:
        # publish …
        orchestrator.record_publish(campaign_id="camp-001", platform="tiktok", spend_amount=0.5)
"""
from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Default limits (all overridable per-campaign)
_DEFAULT_DAILY_PUBLISH_LIMIT = 5
_DEFAULT_DAILY_SPEND_LIMIT = 100.0
_DEFAULT_HOURLY_RATE_LIMIT = 3
# Overage alert threshold: alert when utilisation ≥ this fraction
_OVERAGE_ALERT_THRESHOLD = 0.85

# Quota counter dict-keys (single source of truth for persistence merge)
_QUOTA_COUNT_KEYS = ("publish_counts", "spend_totals", "hourly_counts", "platform_counts")

# In-memory store: {campaign_id → quota_state}
_QUOTA_STORE: dict[str, dict[str, Any]] = {}


def _day_key() -> str:
    """Return current UTC date as YYYYMMDD string."""
    import time as _time
    t = _time.gmtime()
    return f"{t.tm_year:04d}{t.tm_mon:02d}{t.tm_mday:02d}"


def _hour_key() -> str:
    """Return current UTC date+hour as YYYYMMDDHH string."""
    import time as _time
    t = _time.gmtime()
    return f"{t.tm_year:04d}{t.tm_mon:02d}{t.tm_mday:02d}{t.tm_hour:02d}"


class PortfolioQuotaOrchestrator:
    """Multi-dimensional quota tracking and enforcement across a portfolio.

    Tracks:
    - Per-campaign daily publish count and spend.
    - Per-campaign hourly publish rate.
    - Per-platform daily capacity across all campaigns.
    - Overage history for alerting.

    All state is in-memory and resets per day/hour automatically via key
    rotation.  Provide a ``db`` for persistent quota tracking.
    """

    def __init__(
        self,
        db: Any | None = None,
        default_daily_publish_limit: int = _DEFAULT_DAILY_PUBLISH_LIMIT,
        default_daily_spend_limit: float = _DEFAULT_DAILY_SPEND_LIMIT,
        default_hourly_rate_limit: int = _DEFAULT_HOURLY_RATE_LIMIT,
    ) -> None:
        self._db = db
        self._default_daily_publish_limit = default_daily_publish_limit
        self._default_daily_spend_limit = default_daily_spend_limit
        self._default_hourly_rate_limit = default_hourly_rate_limit

    # ------------------------------------------------------------------
    # Campaign registration
    # ------------------------------------------------------------------

    def register_campaign(
        self,
        campaign_id: str,
        daily_publish_limit: int | None = None,
        daily_spend_limit: float | None = None,
        hourly_rate_limit: int | None = None,
        platform_quotas: dict[str, int] | None = None,
    ) -> None:
        """Register (or update) quota limits for a campaign.

        ``platform_quotas`` maps platform name → max daily publishes on that
        platform specifically for this campaign.
        """
        if campaign_id not in _QUOTA_STORE:
            _QUOTA_STORE[campaign_id] = {}

        _QUOTA_STORE[campaign_id].update({
            "daily_publish_limit": daily_publish_limit or self._default_daily_publish_limit,
            "daily_spend_limit": daily_spend_limit or self._default_daily_spend_limit,
            "hourly_rate_limit": hourly_rate_limit or self._default_hourly_rate_limit,
            "platform_quotas": platform_quotas or {},
            "publish_counts": {},   # day_key → count
            "spend_totals": {},     # day_key → spend
            "hourly_counts": {},    # hour_key → count
            "platform_counts": {},  # (day_key, platform) → count
            "overage_count": 0,
            "last_registered_at": time.time(),
        })

    # ------------------------------------------------------------------
    # Quota check (read-only, does not mutate state)
    # ------------------------------------------------------------------

    def check_quota(
        self,
        campaign_id: str,
        platform: str | None = None,
        spend_amount: float = 0.0,
    ) -> dict[str, Any]:
        """Check whether a publish is within quota limits.

        Returns:
            Dict with ``allowed`` (bool), ``reasons`` (list of violation
            strings if not allowed), and ``quota_remaining`` per dimension.
        """
        state = self._get_or_init(campaign_id)
        day = _day_key()
        hour = _hour_key()
        reasons: list[str] = []

        # Daily publish count
        daily_count = state["publish_counts"].get(day, 0)
        daily_limit = state["daily_publish_limit"]
        daily_remaining = max(0, daily_limit - daily_count)
        if daily_count >= daily_limit:
            reasons.append(f"daily_publish_limit_reached:{daily_count}/{daily_limit}")

        # Daily spend
        daily_spend = state["spend_totals"].get(day, 0.0)
        spend_limit = state["daily_spend_limit"]
        spend_remaining = max(0.0, spend_limit - daily_spend)
        if daily_spend + spend_amount > spend_limit:
            reasons.append(f"daily_spend_limit_exceeded:{daily_spend + spend_amount:.2f}>{spend_limit:.2f}")

        # Hourly rate
        hourly_count = state["hourly_counts"].get(hour, 0)
        hourly_limit = state["hourly_rate_limit"]
        hourly_remaining = max(0, hourly_limit - hourly_count)
        if hourly_count >= hourly_limit:
            reasons.append(f"hourly_rate_limit_reached:{hourly_count}/{hourly_limit}")

        # Platform-specific quota
        platform_remaining: int | None = None
        if platform:
            pk = f"{day}:{platform}"
            platform_count = state["platform_counts"].get(pk, 0)
            platform_limit = state["platform_quotas"].get(platform, daily_limit)
            platform_remaining = max(0, platform_limit - platform_count)
            if platform_count >= platform_limit:
                reasons.append(f"platform_quota_reached:{platform}:{platform_count}/{platform_limit}")

        return {
            "allowed": len(reasons) == 0,
            "campaign_id": campaign_id,
            "platform": platform,
            "reasons": reasons,
            "quota_remaining": {
                "daily_publishes": daily_remaining,
                "daily_spend": round(spend_remaining, 4),
                "hourly_rate": hourly_remaining,
                "platform": platform_remaining,
            },
        }

    # ------------------------------------------------------------------
    # Record a publish (mutates state)
    # ------------------------------------------------------------------

    def record_publish(
        self,
        campaign_id: str,
        platform: str | None = None,
        spend_amount: float = 0.0,
    ) -> None:
        """Update quota counters after a successful publish."""
        state = self._get_or_init(campaign_id)
        day = _day_key()
        hour = _hour_key()

        state["publish_counts"][day] = state["publish_counts"].get(day, 0) + 1
        state["spend_totals"][day] = state["spend_totals"].get(day, 0.0) + spend_amount
        state["hourly_counts"][hour] = state["hourly_counts"].get(hour, 0) + 1
        if platform:
            pk = f"{day}:{platform}"
            state["platform_counts"][pk] = state["platform_counts"].get(pk, 0) + 1

        # Track overage
        daily_count = state["publish_counts"][day]
        daily_limit = state["daily_publish_limit"]
        if daily_count > daily_limit:
            state["overage_count"] = state.get("overage_count", 0) + 1
            logger.warning(
                "PortfolioQuotaOrchestrator: overage detected campaign=%s count=%d limit=%d",
                campaign_id, daily_count, daily_limit,
            )

    # ------------------------------------------------------------------
    # Portfolio rebalancing
    # ------------------------------------------------------------------

    def rebalance_portfolio(
        self,
        campaign_ids: list[str],
        total_remaining_publishes: int,
    ) -> dict[str, int]:
        """Redistribute remaining publish slots across under-budget campaigns.

        Campaigns that have consumed >= their daily_limit receive 0.
        Remaining slots are distributed proportionally to remaining headroom.

        Returns:
            Dict mapping campaign_id → additional_slots allocated.
        """
        day = _day_key()
        headrooms: dict[str, int] = {}
        for cid in campaign_ids:
            state = self._get_or_init(cid)
            daily_count = state["publish_counts"].get(day, 0)
            daily_limit = state["daily_publish_limit"]
            headroom = max(0, daily_limit - daily_count)
            headrooms[cid] = headroom

        total_headroom = sum(headrooms.values()) or 1
        allocation: dict[str, int] = {}
        allocated = 0
        for cid in campaign_ids:
            share = round(total_remaining_publishes * headrooms[cid] / total_headroom)
            # Cap at the campaign's headroom
            share = min(share, headrooms[cid])
            allocation[cid] = share
            allocated += share

        # Correct for rounding: assign any leftover to the campaign with most headroom
        leftover = total_remaining_publishes - allocated
        if leftover > 0 and headrooms:
            top = max(headrooms, key=lambda c: headrooms[c])
            allocation[top] = allocation.get(top, 0) + leftover

        return allocation

    # ------------------------------------------------------------------
    # Overage alerting
    # ------------------------------------------------------------------

    def overage_alert_summary(
        self,
        campaign_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return campaigns near or at their daily quota limit.

        Args:
            campaign_ids: Campaigns to check. If None, checks all registered.

        Returns:
            List of alert dicts for campaigns at or above
            ``_OVERAGE_ALERT_THRESHOLD`` utilisation.
        """
        ids = campaign_ids or list(_QUOTA_STORE.keys())
        day = _day_key()
        alerts: list[dict[str, Any]] = []
        for cid in ids:
            state = _QUOTA_STORE.get(cid)
            if not state:
                continue
            daily_count = state["publish_counts"].get(day, 0)
            daily_limit = state["daily_publish_limit"]
            utilisation = round(daily_count / max(daily_limit, 1), 4)
            if utilisation >= _OVERAGE_ALERT_THRESHOLD:
                alerts.append({
                    "campaign_id": cid,
                    "utilisation": utilisation,
                    "daily_count": daily_count,
                    "daily_limit": daily_limit,
                    "overage_count": state.get("overage_count", 0),
                    "severity": "critical" if daily_count >= daily_limit else "warning",
                })
        return sorted(alerts, key=lambda a: a["utilisation"], reverse=True)

    # ------------------------------------------------------------------
    # Dashboard snapshot
    # ------------------------------------------------------------------

    def quota_dashboard(
        self,
        campaign_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Return a full portfolio quota status snapshot.

        Returns:
            Dict with ``date_utc``, ``campaigns`` (per-campaign status),
            and ``portfolio_totals``.
        """
        ids = campaign_ids or list(_QUOTA_STORE.keys())
        day = _day_key()
        hour = _hour_key()
        campaigns_status: list[dict[str, Any]] = []
        total_publishes = 0
        total_spend = 0.0

        for cid in ids:
            state = _QUOTA_STORE.get(cid, {})
            daily_count = state.get("publish_counts", {}).get(day, 0)
            daily_spend = state.get("spend_totals", {}).get(day, 0.0)
            hourly_count = state.get("hourly_counts", {}).get(hour, 0)
            daily_limit = state.get("daily_publish_limit", self._default_daily_publish_limit)
            spend_limit = state.get("daily_spend_limit", self._default_daily_spend_limit)
            total_publishes += daily_count
            total_spend += daily_spend
            campaigns_status.append({
                "campaign_id": cid,
                "daily_publishes": daily_count,
                "daily_limit": daily_limit,
                "daily_spend": round(daily_spend, 4),
                "spend_limit": round(spend_limit, 4),
                "hourly_count": hourly_count,
                "overage_count": state.get("overage_count", 0),
                "utilisation": round(daily_count / max(daily_limit, 1), 4),
            })

        return {
            "date_utc": day,
            "campaigns": campaigns_status,
            "portfolio_totals": {
                "total_daily_publishes": total_publishes,
                "total_daily_spend": round(total_spend, 4),
                "campaign_count": len(campaigns_status),
            },
        }

    # ------------------------------------------------------------------
    # DB persistence
    # ------------------------------------------------------------------

    def persist_quota_state(self, campaign_id: str | None = None) -> dict[str, Any]:
        """Persist current quota state to DB for the given campaign (or all).

        Stores a JSON snapshot of the quota state to a publish_quota_snapshot
        table when available, falling back gracefully.

        Returns:
            Dict with ``persisted_campaigns`` count and ``ok``.
        """
        if self._db is None:
            return {"ok": False, "reason": "db_unavailable"}

        ids_to_persist = [campaign_id] if campaign_id else list(_QUOTA_STORE.keys())
        persisted = 0
        try:
            from datetime import datetime, timezone

            for cid in ids_to_persist:
                state = _QUOTA_STORE.get(cid)
                if not state:
                    continue
                self._write_quota_snapshot(cid, state)
                persisted += 1
        except Exception as exc:
            logger.warning("PortfolioQuotaOrchestrator.persist_quota_state failed: %s", exc)
            return {"ok": False, "error": str(exc)}

        return {"ok": True, "persisted_campaigns": persisted}

    def load_quota_state(self, campaign_id: str | None = None) -> dict[str, Any]:
        """Load persisted quota snapshots from DB into in-memory store.

        Only loads state for the current UTC day to avoid stale counters
        from a previous day polluting today's enforcement.

        Returns:
            Dict with ``loaded_campaigns`` count and ``ok``.
        """
        if self._db is None:
            return {"ok": False, "reason": "db_unavailable"}

        loaded = 0
        today = _day_key()
        try:
            rows = self._read_quota_snapshots(campaign_id)
            for row_cid, snapshot in rows:
                # Only load if the snapshot is from today
                if snapshot.get("day_key") != today:
                    continue
                if row_cid not in _QUOTA_STORE:
                    _QUOTA_STORE[row_cid] = snapshot
                else:
                    # Merge: take max counts to avoid under-counting
                    existing = _QUOTA_STORE[row_cid]
                    for count_key in _QUOTA_COUNT_KEYS:
                        for k, v in snapshot.get(count_key, {}).items():
                            current = existing.get(count_key, {}).get(k, 0)
                            existing.setdefault(count_key, {})[k] = max(current, v)
                loaded += 1
        except Exception as exc:
            logger.warning("PortfolioQuotaOrchestrator.load_quota_state failed: %s", exc)
            return {"ok": False, "error": str(exc)}

        return {"ok": True, "loaded_campaigns": loaded}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_or_init(self, campaign_id: str) -> dict[str, Any]:
        """Return quota state for campaign, auto-initialising if not registered."""
        if campaign_id not in _QUOTA_STORE:
            self.register_campaign(campaign_id)
        return _QUOTA_STORE[campaign_id]

    def _write_quota_snapshot(self, campaign_id: str, state: dict[str, Any]) -> None:
        """Write a quota snapshot to DB (best-effort)."""
        try:
            from app.models.publish_job import PublishJob  # type: ignore[import] - used for DB session
            from datetime import datetime, timezone

            snapshot_payload = dict(state)
            snapshot_payload["day_key"] = _day_key()
            snapshot_payload["campaign_id"] = campaign_id

            # Use a simple key-value approach via the DB if a QuotaSnapshot model exists;
            # otherwise store as a JSON column in a generic table.
            try:
                from app.models.quota_snapshot import QuotaSnapshot  # type: ignore[import]

                existing = (
                    self._db.query(QuotaSnapshot)
                    .filter(
                        QuotaSnapshot.campaign_id == campaign_id,
                        QuotaSnapshot.day_key == _day_key(),
                    )
                    .first()
                )
                if existing:
                    existing.payload = snapshot_payload
                    existing.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    self._db.add(existing)
                else:
                    row = QuotaSnapshot(
                        campaign_id=campaign_id,
                        day_key=_day_key(),
                        payload=snapshot_payload,
                        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                    self._db.add(row)
                self._db.commit()
            except ImportError:
                # QuotaSnapshot model not yet created — log and skip
                logger.debug(
                    "PortfolioQuotaOrchestrator: QuotaSnapshot model unavailable, skipping persist"
                )
        except Exception as exc:
            logger.debug("PortfolioQuotaOrchestrator._write_quota_snapshot failed: %s", exc)

    def _read_quota_snapshots(
        self,
        campaign_id: str | None,
    ) -> list[tuple[str, dict[str, Any]]]:
        """Read quota snapshots from DB."""
        try:
            from app.models.quota_snapshot import QuotaSnapshot  # type: ignore[import]

            query = self._db.query(QuotaSnapshot).filter(
                QuotaSnapshot.day_key == _day_key()
            )
            if campaign_id:
                query = query.filter(QuotaSnapshot.campaign_id == campaign_id)
            return [(row.campaign_id, dict(row.payload or {})) for row in query.all()]
        except ImportError:
            return []
        except Exception as exc:
            logger.debug("PortfolioQuotaOrchestrator._read_quota_snapshots failed: %s", exc)
            return []
