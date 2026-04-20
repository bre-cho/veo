"""Unified creative feedback boosts for all creative engines.

Replaces the three near-identical ``_build_feedback_boosts`` / 
``_build_lookbook_feedback_boosts`` / ``_build_motion_feedback_boosts``
helpers with a single, context-aware implementation that:

1. Filters learning store records by **platform**, **market_code**, and
   **goal** before computing boost signals, so the TikTok audience doesn't
   bleed into YouTube scoring and vice versa.
2. Applies stronger boosts when data is contextually aligned (same platform +
   market + goal) and weaker boosts when only partial context matches.
3. Exposes a ``score_weight_recalibration()`` helper that returns adjusted
   scoring-weight multipliers, usable by any engine that needs deeper
   re-weighting beyond a simple per-style additive boost.
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Boost constants
# ---------------------------------------------------------------------------

# Minimum number of winning records before a boost is applied.
_FEEDBACK_WIN_THRESHOLD = 3

# Boost magnitude per tier of winning threshold crossed.
_FEEDBACK_BOOST_STEP = 0.05

# Multiplier applied when all three context dimensions match (platform +
# market + goal).  Partial matches use lower multipliers.
_FULL_CONTEXT_MULTIPLIER = 1.5
_PARTIAL_CONTEXT_MULTIPLIER = 1.0
_NO_CONTEXT_MULTIPLIER = 0.7

# Minimum conversion_score for a record to count as a "win".
_WIN_SCORE_THRESHOLD = 0.7

# Maximum absolute boost any single style can receive.
_MAX_BOOST = 0.20


def build_unified_feedback_boosts(
    learning_store: Any | None,
    *,
    niche: str | None = None,
    platform: str | None = None,
    market_code: str | None = None,
    goal: str | None = None,
) -> dict[str, float]:
    """Return per-style (template_family) additive boosts from learning history.

    The boosts are keyed on ``template_family`` (which creative engines map to
    their own style labels).

    Context matching logic
    ----------------------
    * **Full context** (platform + market_code supplied, both match a record):
      boost multiplied by ``_FULL_CONTEXT_MULTIPLIER``.
    * **Partial context** (only one of platform/market matches):
      boost multiplied by ``_PARTIAL_CONTEXT_MULTIPLIER``.
    * **No context** (niche-only or no filter at all):
      boost multiplied by ``_NO_CONTEXT_MULTIPLIER``.

    This means records from a tightly matching context carry stronger signal
    than generic / cross-platform records.
    """
    if learning_store is None:
        return {}
    try:
        records = learning_store.all_records()
    except Exception:
        return {}

    niche_key = (niche or "").lower()
    platform_key = (platform or "").lower()
    market_key = (market_code or "").lower()
    goal_key = (goal or "").lower()

    # style → list of (score, context_multiplier) tuples
    style_signals: dict[str, list[tuple[float, float]]] = {}

    for rec in records:
        tf = str(rec.get("template_family") or "")
        if not tf:
            continue

        score: float = float(rec.get("conversion_score", 0))
        if score < _WIN_SCORE_THRESHOLD:
            continue

        # Niche filter: skip if niche is specified and record doesn't relate
        if niche_key:
            rec_hook = str(rec.get("hook_pattern") or "").lower()
            rec_tf_lower = tf.lower()
            if niche_key not in rec_hook and niche_key not in rec_tf_lower:
                continue

        # Determine context multiplier
        rec_platform = str(rec.get("platform") or "").lower()
        rec_market = str(rec.get("market_code") or "").lower()
        rec_goal = str(rec.get("template_family") or "").lower()  # goal stored in template_family

        context_dims_matched = 0
        context_dims_requested = 0

        if platform_key:
            context_dims_requested += 1
            if rec_platform == platform_key:
                context_dims_matched += 1

        if market_key:
            context_dims_requested += 1
            if rec_market == market_key:
                context_dims_matched += 1

        if goal_key and context_dims_requested > 0:
            if goal_key in rec_goal:
                context_dims_matched += 1

        if context_dims_requested == 0:
            multiplier = _NO_CONTEXT_MULTIPLIER
        elif context_dims_matched >= context_dims_requested:
            multiplier = _FULL_CONTEXT_MULTIPLIER
        elif context_dims_matched >= 1:
            multiplier = _PARTIAL_CONTEXT_MULTIPLIER
        else:
            multiplier = _NO_CONTEXT_MULTIPLIER

        style_signals.setdefault(tf, []).append((score, multiplier))

    boosts: dict[str, float] = {}
    for style, signals in style_signals.items():
        win_count = len(signals)
        if win_count < _FEEDBACK_WIN_THRESHOLD:
            continue
        # Weighted average multiplier
        avg_multiplier = sum(m for _, m in signals) / len(signals)
        raw_boost = _FEEDBACK_BOOST_STEP * (win_count // _FEEDBACK_WIN_THRESHOLD) * avg_multiplier
        boosts[style] = round(min(_MAX_BOOST, raw_boost), 3)

    return boosts


def score_weight_recalibration(
    learning_store: Any | None,
    base_weights: dict[str, float],
    *,
    platform: str | None = None,
    market_code: str | None = None,
    goal: str | None = None,
    min_records: int = 5,
) -> dict[str, float]:
    """Return multiplicative recalibration factors for ``base_weights``.

    When the learning store has ≥ ``min_records`` context-filtered records,
    returns a dict of the same keys as ``base_weights`` with values in
    ``[0.8, 1.3]`` that represent how much to scale each dimension.

    The method is conservative: factors stay close to 1.0 by default, only
    nudging weights when strong signal exists.  When insufficient data is
    available it returns ``{k: 1.0 ...}`` (no-op).
    """
    neutral = {k: 1.0 for k in base_weights}
    if learning_store is None:
        return neutral
    try:
        summary = learning_store.feedback_summary(platform=platform, market_code=market_code)
    except Exception:
        return neutral

    if summary.get("total_records", 0) < min_records:
        return neutral

    avg_score: float = summary.get("avg_conversion_score", 0.5)
    factors = dict(neutral)

    # Slightly scale conversion-related dimensions based on overall performance
    if avg_score >= 0.75:
        for key in factors:
            if "conversion" in key:
                factors[key] = min(1.3, factors[key] * 1.15)
            elif "audience" in key:
                factors[key] = max(0.85, factors[key] * 0.95)
    elif avg_score < 0.45:
        for key in factors:
            if "audience" in key or "platform" in key or "market" in key or "locali" in key:
                factors[key] = min(1.2, factors[key] * 1.10)
            elif "conversion" in key:
                factors[key] = max(0.80, factors[key] * 0.90)

    return factors
