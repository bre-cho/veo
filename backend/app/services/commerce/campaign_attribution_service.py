"""CampaignAttributionService — multi-touch attribution for campaign conversions.

Phase 1.2: campaign-level attribution supporting last-N-touch model.
Phase 1.5: added time-decay, first-touch, and linear (uniform) attribution
           models; ``campaign_funnel_report`` enriched with per-stage rates,
           average order value, and top-performing variant.

Attribution models
------------------
- ``last_n_touch`` (default): the N most recent touches share equal credit.
- ``time_decay``: credit weighted by recency (exponential decay, half-life 1 day).
- ``first_touch``: 100 % credit to the first touch in the window.
- ``linear``: all touches in the window share equal credit.
"""
from __future__ import annotations

import math
import time
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Default attribution window in days
_DEFAULT_WINDOW_DAYS = 7
# Number of touches to attribute in last-N-touch model
_DEFAULT_N_TOUCH = 3
# Half-life in seconds for time-decay model (default: 1 day)
_TIME_DECAY_HALF_LIFE_SEC = 86400.0
# Supported attribution model names
_ATTRIBUTION_MODELS = ("last_n_touch", "time_decay", "first_touch", "linear")


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
        model: str = "last_n_touch",
    ) -> dict[str, Any]:
        """Attribute a conversion event across campaign variants/creatives.

        Args:
            conversion_event: dict with at minimum ``timestamp`` (UNIX epoch)
                and optionally ``video_id``, ``variant_id`` fields.
            campaign_id: The campaign to attribute within.
            window_days: Look-back window in days.
            n_touch: Max touches (used by last_n_touch model).
            model: Attribution model — one of ``last_n_touch``, ``time_decay``,
                ``first_touch``, or ``linear``.

        Returns:
            Dict with ``campaign_id``, ``total_attributed_value``,
            ``attributions`` list (per variant/creative with ``credit`` share),
            ``window_days``, and ``attribution_model``.
        """
        now = conversion_event.get("timestamp") or time.time()
        window_start = now - window_days * 86400

        # Retrieve touchpoints from the learning store when available
        touchpoints = self._get_touchpoints(
            campaign_id=campaign_id,
            window_start=window_start,
            current_time=float(now),
        )

        # Sort by recency (most recent first)
        touchpoints.sort(
            key=lambda tp: float(tp.get("recorded_at", 0)), reverse=True
        )

        conversion_value = float(conversion_event.get("value", 1.0))

        if model == "first_touch":
            attributions = self._first_touch(touchpoints, conversion_value)
        elif model == "time_decay":
            attributions = self._time_decay(touchpoints, conversion_value, float(now))
        elif model == "linear":
            attributions = self._linear(touchpoints, conversion_value)
        else:
            # Default: last_n_touch
            attributions = self._last_n_touch(touchpoints, conversion_value, n_touch)

        return {
            "campaign_id": campaign_id,
            "window_days": window_days,
            "n_touch": n_touch,
            "attribution_model": model,
            "total_attributed_value": round(conversion_value, 4),
            "attributions": attributions,
            "touchpoint_count": len(attributions),
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
            ``conversion_rate`` (purchases / clicks),
            ``avg_order_value``, ``revenue_estimate``,
            and ``top_variant`` (variant_id with highest conversion_score).
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

        # Average order value from performance_metrics.order_value when available
        order_values = [
            float((r.get("performance_metrics") or {}).get("order_value", 0.0))
            for r in records
            if float((r.get("performance_metrics") or {}).get("order_value", 0.0)) > 0
        ]
        avg_order_value = round(sum(order_values) / len(order_values), 4) if order_values else 0.0
        revenue_estimate = round(purchases * avg_order_value, 4)

        # Top variant: highest mean conversion_score
        variant_scores: dict[str, list[float]] = {}
        for r in records:
            vid = r.get("variant_id")
            if vid:
                variant_scores.setdefault(vid, []).append(float(r.get("conversion_score", 0.0)))
        top_variant: str | None = None
        if variant_scores:
            top_variant = max(
                variant_scores.keys(),
                key=lambda v: sum(variant_scores[v]) / len(variant_scores[v]),
            )

        return {
            "campaign_id": campaign_id,
            "record_count": len(records),
            "impressions": impressions,
            "clicks": clicks,
            "purchases": purchases,
            "ctr": ctr,
            "conversion_rate": conversion_rate,
            "avg_order_value": avg_order_value,
            "revenue_estimate": revenue_estimate,
            "top_variant": top_variant,
        }

    # ------------------------------------------------------------------
    # Attribution model implementations
    # ------------------------------------------------------------------

    def _last_n_touch(
        self,
        touchpoints: list[dict[str, Any]],
        total_value: float,
        n_touch: int,
    ) -> list[dict[str, Any]]:
        """Equal credit across the N most recent touches."""
        selected = touchpoints[:n_touch]
        credit = round(total_value / max(len(selected), 1), 4)
        return [
            {
                "video_id": tp.get("video_id"),
                "variant_id": tp.get("variant_id"),
                "hook_pattern": tp.get("hook_pattern"),
                "credit": credit,
                "recorded_at": tp.get("recorded_at"),
            }
            for tp in selected
        ]

    def _time_decay(
        self,
        touchpoints: list[dict[str, Any]],
        total_value: float,
        now: float,
    ) -> list[dict[str, Any]]:
        """Credit weighted by recency (exponential decay; half-life = 1 day)."""
        if not touchpoints:
            return []
        decay_weights: list[float] = []
        for tp in touchpoints:
            age_sec = max(0.0, now - float(tp.get("recorded_at", now)))
            w = math.pow(0.5, age_sec / _TIME_DECAY_HALF_LIFE_SEC)
            decay_weights.append(w)
        total_w = sum(decay_weights) or 1.0
        return [
            {
                "video_id": tp.get("video_id"),
                "variant_id": tp.get("variant_id"),
                "hook_pattern": tp.get("hook_pattern"),
                "credit": round(total_value * (decay_weights[i] / total_w), 4),
                "recorded_at": tp.get("recorded_at"),
            }
            for i, tp in enumerate(touchpoints)
        ]

    @staticmethod
    def _first_touch(
        touchpoints: list[dict[str, Any]],
        total_value: float,
    ) -> list[dict[str, Any]]:
        """100 % credit to the oldest touch (first in the window)."""
        if not touchpoints:
            return []
        # touchpoints are sorted most-recent first; first touch = last element
        first = sorted(touchpoints, key=lambda tp: float(tp.get("recorded_at", 0)))[0]
        return [
            {
                "video_id": first.get("video_id"),
                "variant_id": first.get("variant_id"),
                "hook_pattern": first.get("hook_pattern"),
                "credit": round(total_value, 4),
                "recorded_at": first.get("recorded_at"),
            }
        ]

    @staticmethod
    def _linear(
        touchpoints: list[dict[str, Any]],
        total_value: float,
    ) -> list[dict[str, Any]]:
        """Equal credit across ALL touches in the window."""
        if not touchpoints:
            return []
        credit = round(total_value / len(touchpoints), 4)
        return [
            {
                "video_id": tp.get("video_id"),
                "variant_id": tp.get("variant_id"),
                "hook_pattern": tp.get("hook_pattern"),
                "credit": credit,
                "recorded_at": tp.get("recorded_at"),
            }
            for tp in touchpoints
        ]

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
        # Use a 60-second tolerance for the upper bound to handle slight timing
        # differences between when the conversion timestamp was captured and
        # when performance records were actually stored.
        upper_bound = current_time + 60.0
        return [
            r for r in records
            if float(r.get("recorded_at", 0)) >= window_start
               and float(r.get("recorded_at", 0)) <= upper_bound
        ]
