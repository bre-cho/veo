"""template_scorecard — compute derived template performance scores from raw metrics.

Scoring formulas
----------------
hook_score      = ctr * 100
retention_score = 0.6 * retention_30s + 0.4 * avg_watch_ratio
engagement_score= 0.4 * like_rate + 0.3 * comment_rate + 0.3 * share_rate
conversion_score= 0.7 * subscribe_rate + 0.3 * series_continue_rate

total_score     = 0.30 * hook_score
                + 0.35 * retention_score
                + 0.15 * engagement_score
                + 0.20 * conversion_score   (0–100 range)

Tier thresholds
---------------
>= 85  → WINNER  (promote to PatternMemory as template_winner)
75–84  → STRONG  (priority test candidate)
60–74  → NORMAL  (keep but do not scale)
< 60   → REJECT  (reduce selector weight)
"""
from __future__ import annotations

from typing import Any

_TIER_WINNER = "winner"
_TIER_STRONG = "strong"
_TIER_NORMAL = "normal"
_TIER_REJECT = "reject"

_THRESHOLD_WINNER = 85.0
_THRESHOLD_STRONG = 75.0
_THRESHOLD_NORMAL = 60.0


def compute_template_score(metrics: dict[str, Any]) -> dict[str, float]:
    """Return a dict with hook/retention/engagement/conversion/total scores.

    All inputs are expected to be fractions in [0, 1] except ``ctr`` which
    is also in [0, 1] (e.g. 0.05 for 5 %).  Outputs are in [0, 100].
    """
    ctr = float(metrics.get("ctr") or 0.0)
    retention_30s = float(metrics.get("retention_30s") or 0.0)
    avg_watch_ratio = float(metrics.get("avg_watch_ratio") or 0.0)
    like_rate = float(metrics.get("like_rate") or 0.0)
    comment_rate = float(metrics.get("comment_rate") or 0.0)
    share_rate = float(metrics.get("share_rate") or 0.0)
    subscribe_rate = float(metrics.get("subscribe_rate") or 0.0)
    series_continue_rate = float(metrics.get("series_continue_rate") or 0.0)

    hook_score = ctr * 100.0
    retention_score = 0.6 * retention_30s * 100.0 + 0.4 * avg_watch_ratio * 100.0
    engagement_score = (0.4 * like_rate + 0.3 * comment_rate + 0.3 * share_rate) * 100.0
    conversion_score = (0.7 * subscribe_rate + 0.3 * series_continue_rate) * 100.0

    total_score = (
        0.30 * hook_score
        + 0.35 * retention_score
        + 0.15 * engagement_score
        + 0.20 * conversion_score
    )

    return {
        "hook_score": round(hook_score, 4),
        "retention_score": round(retention_score, 4),
        "engagement_score": round(engagement_score, 4),
        "conversion_score": round(conversion_score, 4),
        "total_score": round(total_score, 4),
    }


def classify_template_tier(total_score: float) -> str:
    """Return tier string based on total_score (0–100)."""
    if total_score >= _THRESHOLD_WINNER:
        return _TIER_WINNER
    if total_score >= _THRESHOLD_STRONG:
        return _TIER_STRONG
    if total_score >= _THRESHOLD_NORMAL:
        return _TIER_NORMAL
    return _TIER_REJECT
