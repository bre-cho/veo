"""Unit tests for the unified creative_feedback module."""
from __future__ import annotations

import pytest

from app.services.creative_feedback import build_unified_feedback_boosts, score_weight_recalibration
from app.services.learning_engine import PerformanceLearningEngine


def _engine(tmp_path, n: int = 0) -> PerformanceLearningEngine:
    eng = PerformanceLearningEngine(store_path=str(tmp_path / "store.json"))
    eng.clear()
    return eng


def _seed(eng: PerformanceLearningEngine, *, n: int = 5, platform: str = "tiktok", market_code: str = "VN", score: float = 0.85, tf: str = "ugc") -> None:
    for i in range(n):
        eng.record(
            video_id=f"{platform}-{tf}-{i}",
            hook_pattern=f"hook-{tf}",
            cta_pattern="cta-buy",
            template_family=tf,
            conversion_score=score,
            platform=platform,
            market_code=market_code,
        )


# ---------------------------------------------------------------------------
# build_unified_feedback_boosts
# ---------------------------------------------------------------------------


class TestBuildUnifiedFeedbackBoosts:
    def test_returns_empty_when_store_is_none(self) -> None:
        result = build_unified_feedback_boosts(None)
        assert result == {}

    def test_returns_empty_when_fewer_than_threshold_wins(self, tmp_path) -> None:
        eng = _engine(tmp_path)
        _seed(eng, n=2, score=0.9)  # 2 < _FEEDBACK_WIN_THRESHOLD=3
        result = build_unified_feedback_boosts(eng)
        assert result == {}

    def test_returns_boost_for_winning_style(self, tmp_path) -> None:
        eng = _engine(tmp_path)
        _seed(eng, n=5, tf="ugc", score=0.9)
        result = build_unified_feedback_boosts(eng)
        assert "ugc" in result
        assert result["ugc"] > 0

    def test_full_context_boost_greater_than_no_context(self, tmp_path) -> None:
        """Records matching platform+market should give higher boost."""
        eng = _engine(tmp_path)
        _seed(eng, n=5, platform="tiktok", market_code="VN", score=0.9, tf="dynamic")

        # Full context
        boost_full = build_unified_feedback_boosts(
            eng, platform="tiktok", market_code="VN"
        ).get("dynamic", 0.0)

        # No context
        boost_none = build_unified_feedback_boosts(eng).get("dynamic", 0.0)

        assert boost_full >= boost_none

    def test_low_score_records_not_boosted(self, tmp_path) -> None:
        eng = _engine(tmp_path)
        _seed(eng, n=10, score=0.5, tf="editorial")  # below _WIN_SCORE_THRESHOLD
        result = build_unified_feedback_boosts(eng)
        assert result.get("editorial", 0.0) == 0.0

    def test_boost_capped_at_max(self, tmp_path) -> None:
        eng = _engine(tmp_path)
        _seed(eng, n=50, score=0.99, tf="mega-style")
        result = build_unified_feedback_boosts(eng)
        for v in result.values():
            assert v <= 0.20  # _MAX_BOOST

    def test_niche_filter_excludes_unrelated_records(self, tmp_path) -> None:
        eng = _engine(tmp_path)
        # Records for "fashion" niche
        for i in range(5):
            eng.record(
                video_id=f"fashion-{i}",
                hook_pattern="fashion-hook",
                cta_pattern="cta",
                template_family="fashion-style",
                conversion_score=0.9,
            )
        # No records for "fitness"
        result = build_unified_feedback_boosts(eng, niche="fitness")
        assert result.get("fashion-style", 0.0) == 0.0


# ---------------------------------------------------------------------------
# score_weight_recalibration
# ---------------------------------------------------------------------------


class TestScoreWeightRecalibration:
    _BASE = {"conversion_potential": 0.20, "audience_fit": 0.22, "platform_fit": 0.20, "repeatability": 0.18, "product_fit": 0.20}

    def test_returns_neutral_when_no_store(self) -> None:
        factors = score_weight_recalibration(None, self._BASE)
        assert all(v == 1.0 for v in factors.values())

    def test_returns_neutral_when_insufficient_records(self, tmp_path) -> None:
        eng = _engine(tmp_path)
        _seed(eng, n=3, score=0.9)  # < min_records=5
        factors = score_weight_recalibration(eng, self._BASE, min_records=5)
        assert all(v == 1.0 for v in factors.values())

    def test_high_avg_boosts_conversion_dimension(self, tmp_path) -> None:
        eng = _engine(tmp_path)
        _seed(eng, n=10, score=0.9)  # high conversion
        factors = score_weight_recalibration(eng, self._BASE)
        assert factors.get("conversion_potential", 1.0) > 1.0

    def test_low_avg_boosts_audience_dimension(self, tmp_path) -> None:
        eng = _engine(tmp_path)
        _seed(eng, n=10, score=0.35)  # low conversion
        factors = score_weight_recalibration(eng, self._BASE)
        assert factors.get("audience_fit", 1.0) >= 1.0

    def test_factors_within_bounds(self, tmp_path) -> None:
        eng = _engine(tmp_path)
        _seed(eng, n=10, score=0.99)
        factors = score_weight_recalibration(eng, self._BASE)
        for v in factors.values():
            assert 0.79 <= v <= 1.31


# ---------------------------------------------------------------------------
# Integration: TrendImageEngine uses unified feedback
# ---------------------------------------------------------------------------


def test_trend_image_engine_with_unified_feedback(tmp_path) -> None:
    from app.schemas.trend_image import TrendImageRequest
    from app.services.trend_image_engine import TrendImageEngine

    eng = _engine(tmp_path)
    _seed(eng, n=5, score=0.9, tf="ugc")

    engine = TrendImageEngine()
    req = TrendImageRequest(topic="fitness tips", niche="fitness", count=3)
    result = engine.generate(req, learning_store=eng)
    assert result.candidates
    assert result.recommended_winner_id


def test_lookbook_engine_with_unified_feedback(tmp_path) -> None:
    from app.schemas.lookbook import LookbookRequest
    from app.services.lookbook_engine import LookbookEngine

    eng = _engine(tmp_path)
    _seed(eng, n=5, score=0.9, tf="ugc-dynamic")

    engine = LookbookEngine()
    products = [{"name": "Jacket", "style": "street"}, {"name": "Pants", "style": "street"}]
    req = LookbookRequest(products=products, target_platform="tiktok", market_code="VN")
    result = engine.generate(req, learning_store=eng)
    assert result.winner_candidate_id


def test_motion_clone_engine_with_unified_feedback(tmp_path) -> None:
    from app.schemas.motion_clone import MotionCloneRequest
    from app.services.motion_clone_engine import MotionCloneEngine

    eng = _engine(tmp_path)
    _seed(eng, n=5, score=0.9, tf="balanced")

    engine = MotionCloneEngine()
    req = MotionCloneRequest(reference_motion_text="fast rhythm", market_code="VN")
    result = engine.plan(req, learning_store=eng)
    assert result.winner_candidate_id
