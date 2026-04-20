"""CampaignAttributionService — multi-touch attribution for campaign conversions.

Phase 1.2: campaign-level attribution supporting last-N-touch model.
"""
from __future__ import annotations

import time
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Default attribution window in days
_DEFAULT_WINDOW_DAYS = 7
# Number of touches to attribute in last-N-touch model
_DEFAULT_N_TOUCH = 3


class CampaignAttributionService:
    """Attribute conversion events to campaign creatives using last-N-touch model.

    ``attribute_conversion()`` distributes conversion credit across up to N
    recent variant/creative interactions within the attribution window.
    ``campaign_funnel_report()`` aggregates impressions → clicks → purchases.
    """

    def __init__(self, learning_store: Any | None = None) -> None:
        self._learning_store = learning_store

    def attribute_conversion(
        self,
        conversion_event: dict[str, Any],
        campaign_id: str,
        window_days: int = _DEFAULT_WINDOW_DAYS,
        n_touch: int = _DEFAULT_N_TOUCH,
    ) -> dict[str, Any]:
        """Attribute a conversion event across campaign variants/creatives.

        Uses last-N-touch model: the N most recent touchpoints before
        conversion each receive equal fractional credit (1/N).

        Args:
            conversion_event: dict with at minimum ``timestamp`` (UNIX epoch)
                and optionally ``video_id``, ``variant_id`` fields.
            campaign_id: The campaign to attribute within.
            window_days: Look-back window in days.
            n_touch: Number of touches to split credit across.

        Returns:
            Dict with ``campaign_id``, ``total_attributed_value``,
            ``attributions`` list (per variant/creative with ``credit`` share),
            and ``window_days``.
        """
        now = conversion_event.get("timestamp") or time.time()
        window_start = now - window_days * 86400

        # Retrieve touchpoints from the learning store when available
        touchpoints = self._get_touchpoints(
            campaign_id=campaign_id,
            window_start=window_start,
            current_time=float(now),
        )

        # Sort by recency (most recent first) and take up to N
        touchpoints_in_window = [
            tp for tp in touchpoints
            if float(tp.get("recorded_at", 0)) >= window_start
        ]
        touchpoints_in_window.sort(
            key=lambda tp: float(tp.get("recorded_at", 0)), reverse=True
        )
        selected = touchpoints_in_window[:n_touch]

        conversion_value = float(conversion_event.get("value", 1.0))
        credit_per_touch = round(conversion_value / max(len(selected), 1), 4)

        attributions = []
        for tp in selected:
            attributions.append(
                {
                    "video_id": tp.get("video_id"),
                    "variant_id": tp.get("variant_id"),
                    "hook_pattern": tp.get("hook_pattern"),
                    "credit": credit_per_touch,
                    "recorded_at": tp.get("recorded_at"),
                }
            )

        return {
            "campaign_id": campaign_id,
            "window_days": window_days,
            "n_touch": n_touch,
            "total_attributed_value": round(conversion_value, 4),
            "attributions": attributions,
            "touchpoint_count": len(selected),
        }

    def campaign_funnel_report(
        self,
        campaign_id: str,
    ) -> dict[str, Any]:
        """Return a funnel summary for a campaign.

        Aggregates impressions → clicks → purchases from performance records
        associated with this campaign_id.

        Returns:
            Dict with ``campaign_id``, ``impressions``, ``clicks``,
            ``purchases``, ``ctr`` (click-through rate),
            and ``conversion_rate`` (purchases / clicks).
        """
        records = self._get_campaign_records(campaign_id)

        impressions = sum(int(r.get("view_count", 0)) for r in records)
        clicks = sum(
            int(round(float(r.get("click_through_rate", 0.0)) * int(r.get("view_count", 0))))
            for r in records
        )
        # Purchases: records where conversion_score >= 0.5 treated as conversions
        purchases = sum(
            1 for r in records if float(r.get("conversion_score", 0.0)) >= 0.5
        )

        ctr = round(clicks / max(impressions, 1), 4)
        conversion_rate = round(purchases / max(clicks, 1), 4)

        return {
            "campaign_id": campaign_id,
            "record_count": len(records),
            "impressions": impressions,
            "clicks": clicks,
            "purchases": purchases,
            "ctr": ctr,
            "conversion_rate": conversion_rate,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_campaign_records(self, campaign_id: str) -> list[dict[str, Any]]:
        """Return all performance records for a campaign."""
        if self._learning_store is None:
            return []
        try:
            all_records = self._learning_store.all_records()
            return [r for r in all_records if r.get("campaign_id") == campaign_id]
        except Exception:
            return []

    def _get_touchpoints(
        self,
        campaign_id: str,
        window_start: float,
        current_time: float,
    ) -> list[dict[str, Any]]:
        """Retrieve touchpoints (performance records) for the campaign in the window."""
        records = self._get_campaign_records(campaign_id)
        return [
            r for r in records
            if float(r.get("recorded_at", 0)) >= window_start
               and float(r.get("recorded_at", 0)) <= current_time
        ]
