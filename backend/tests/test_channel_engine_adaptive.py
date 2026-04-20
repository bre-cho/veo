"""Unit tests for adaptive scoring in ChannelEngine (C-layer)."""
from __future__ import annotations

import pytest

from app.schemas.channel import ChannelPlanRequest
from app.services.channel_engine import (
    ChannelEngine,
    _apply_weight_adjustments,
    _derive_adaptive_weight_adjustments,
    _ADAPTIVE_MIN_RECORDS,
    _MAX_WEIGHT_ADJUSTMENT,
    _SCORE_WEIGHTS,
)
from app.services.learning_engine import PerformanceLearningEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_learning_store(
    tmp_path,
    n: int = 10,
    conversion_score: float = 0.8,
    hook_pattern: str = "hook-stable",
) -> PerformanceLearningEngine:
    store_path = str(tmp_path / "store.json")
    eng = PerformanceLearningEngine(store_path=store_path)
    eng.clear()
    for i in range(n):
        eng.record(
            video_id=f"v{i}",
            hook_pattern=hook_pattern,
            cta_pattern="cta-x",
            template_family="family-x",
            conversion_score=conversion_score,
        )
    return eng


# ---------------------------------------------------------------------------
# _derive_adaptive_weight_adjustments()
# ---------------------------------------------------------------------------


def test_no_adjustment_when_store_is_none() -> None:
    assert _derive_adaptive_weight_adjustments(None) == {}


def test_no_adjustment_when_fewer_than_min_records(tmp_path) -> None:
    eng = _make_learning_store(tmp_path, n=_ADAPTIVE_MIN_RECORDS - 1)
    assert _derive_adaptive_weight_adjustments(eng) == {}


def test_high_conversion_boosts_conversion_potential(tmp_path) -> None:
    eng = _make_learning_store(tmp_path, n=10, conversion_score=0.9)
    adj = _derive_adaptive_weight_adjustments(eng)
    assert adj.get("conversion_potential", 0) > 0


def test_low_conversion_boosts_audience_fit(tmp_path) -> None:
    eng = _make_learning_store(tmp_path, n=10, conversion_score=0.3)
    adj = _derive_adaptive_weight_adjustments(eng)
    assert adj.get("audience_fit", 0) > 0
    assert adj.get("platform_fit", 0) > 0


def test_stable_hook_pattern_boosts_repeatability(tmp_path) -> None:
    eng = _make_learning_store(tmp_path, n=10, conversion_score=0.9, hook_pattern="hook-x")
    adj = _derive_adaptive_weight_adjustments(eng)
    assert adj.get("repeatability", 0) > 0


def test_adjustments_clamped_to_max(tmp_path) -> None:
    eng = _make_learning_store(tmp_path, n=20, conversion_score=0.99)
    adj = _derive_adaptive_weight_adjustments(eng)
    for v in adj.values():
        assert abs(v) <= _MAX_WEIGHT_ADJUSTMENT


# ---------------------------------------------------------------------------
# _apply_weight_adjustments()
# ---------------------------------------------------------------------------


def test_apply_weight_adjustments_normalises_to_one() -> None:
    adj = {"conversion_potential": 0.03, "audience_fit": -0.01}
    result = _apply_weight_adjustments(_SCORE_WEIGHTS, adj)
    assert abs(sum(result.values()) - 1.0) < 0.001


def test_apply_weight_adjustments_no_zero_weights() -> None:
    adj = {k: -0.05 for k in _SCORE_WEIGHTS}  # large negative
    result = _apply_weight_adjustments(_SCORE_WEIGHTS, adj)
    assert all(v >= 0.05 for v in result.values())


# ---------------------------------------------------------------------------
# ChannelEngine.generate_plan() – adaptive scoring integration
# ---------------------------------------------------------------------------


def test_generate_plan_with_no_learning_store() -> None:
    engine = ChannelEngine()
    req = ChannelPlanRequest(niche="fitness", days=3)
    result = engine.generate_plan(req)
    assert result.candidates
    assert result.winner_candidate_id
    # feedback_applied should be False when no learning store provided
    for c in result.candidates:
        assert c.metadata.get("feedback_applied") is False


def test_generate_plan_with_learning_store_marks_feedback_applied(tmp_path) -> None:
    engine = ChannelEngine()
    store = _make_learning_store(tmp_path, n=10, conversion_score=0.85)
    req = ChannelPlanRequest(niche="fitness", days=3, goal="conversion")
    result = engine.generate_plan(req, learning_store=store)
    assert result.candidates
    # At least some candidates should have feedback_applied=True
    applied = [c for c in result.candidates if c.metadata.get("feedback_applied")]
    assert applied


def test_generate_plan_produces_valid_series(tmp_path) -> None:
    engine = ChannelEngine()
    store = _make_learning_store(tmp_path, n=6, conversion_score=0.6)
    req = ChannelPlanRequest(niche="beauty", days=5, posts_per_day=2)
    result = engine.generate_plan(req, learning_store=store)
    assert len(result.series_plan) == 10  # 5 days × 2 posts


def test_generate_plan_winner_has_highest_score(tmp_path) -> None:
    engine = ChannelEngine()
    store = _make_learning_store(tmp_path, n=8, conversion_score=0.4)
    req = ChannelPlanRequest(niche="tech", days=2)
    result = engine.generate_plan(req, learning_store=store)
    winner = next(c for c in result.candidates if c.winner_flag)
    non_winners = [c for c in result.candidates if not c.winner_flag]
    assert all(winner.score_total >= c.score_total for c in non_winners)

