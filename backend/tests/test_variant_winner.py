"""Test variant winner selection and adaptive scoring."""
from __future__ import annotations

import os
import tempfile

import pytest

from app.services.learning_engine import PerformanceLearningEngine


@pytest.fixture()
def tmp_store(tmp_path):
    store_path = str(tmp_path / "test_store.json")
    yield store_path


@pytest.fixture()
def engine(tmp_store):
    eng = PerformanceLearningEngine(store_path=tmp_store)
    eng.clear()
    return eng


def _inject_records(engine: PerformanceLearningEngine, experiment_id: str) -> None:
    """Inject 5 synthetic records for 2 variants (3 for winner, 2 for loser)."""
    # Variant A: high-performing (avg score ~0.85)
    variant_a_id = "variant-A"
    for i in range(3):
        engine.record(
            video_id=f"vid-A-{i}",
            hook_pattern="curiosity_hook",
            cta_pattern="discount_cta",
            template_family="conversion",
            conversion_score=0.85 + i * 0.01,
            platform="tiktok",
            experiment_id=experiment_id,
            variant_id=variant_a_id,
        )

    # Variant B: low-performing (avg score ~0.45)
    variant_b_id = "variant-B"
    for i in range(2):
        engine.record(
            video_id=f"vid-B-{i}",
            hook_pattern="generic_hook",
            cta_pattern="generic_cta",
            template_family="engagement",
            conversion_score=0.45 + i * 0.01,
            platform="tiktok",
            experiment_id=experiment_id,
            variant_id=variant_b_id,
        )


class TestExperimentWinnerSelection:
    def test_winner_is_variant_a(self, engine):
        experiment_id = "exp-001"
        _inject_records(engine, experiment_id)

        summary = engine.experiment_summary(experiment_id=experiment_id)
        assert summary["winner_variant_id"] == "variant-A"

    def test_loser_adaptive_score_lower_by_5pct(self, engine):
        experiment_id = "exp-002"
        _inject_records(engine, experiment_id)

        winner_score = engine.adaptive_score(
            template_family="conversion",
            hook_pattern="curiosity_hook",
            platform="tiktok",
        )
        loser_score = engine.adaptive_score(
            template_family="engagement",
            hook_pattern="generic_hook",
            platform="tiktok",
        )
        # Winner should score at least 5% higher than loser
        assert winner_score >= loser_score + 0.05, (
            f"Expected winner ({winner_score:.3f}) >= loser ({loser_score:.3f}) + 0.05"
        )

    def test_winner_has_highest_avg_score(self, engine):
        experiment_id = "exp-003"
        _inject_records(engine, experiment_id)

        summary = engine.experiment_summary(experiment_id=experiment_id)
        variants = summary["variants"]
        assert len(variants) == 2
        winner = next(v for v in variants if v["variant_id"] == "variant-A")
        loser = next(v for v in variants if v["variant_id"] == "variant-B")
        assert winner["avg_score"] > loser["avg_score"]

    def test_product_id_filter(self, engine):
        """Test that product_id filtering works in feedback_summary."""
        engine.record(
            video_id="prod-vid-1",
            hook_pattern="product_hook",
            cta_pattern="product_cta",
            template_family="conversion",
            conversion_score=0.90,
            product_id="product-XYZ",
        )
        engine.record(
            video_id="prod-vid-2",
            hook_pattern="other_hook",
            cta_pattern="other_cta",
            template_family="engagement",
            conversion_score=0.30,
            product_id="other-product",
        )

        summary = engine.feedback_summary(product_id="product-XYZ")
        assert summary["total_records"] == 1
        assert summary["avg_conversion_score"] == pytest.approx(0.90, abs=0.01)

    def test_persona_id_filter(self, engine):
        """Test that persona_id (avatar_id) filtering works."""
        engine.record(
            video_id="persona-vid-1",
            hook_pattern="persona_hook",
            cta_pattern="persona_cta",
            template_family="retention",
            conversion_score=0.80,
            avatar_id="avatar-123",
        )
        engine.record(
            video_id="persona-vid-2",
            hook_pattern="other_hook",
            cta_pattern="other_cta",
            template_family="awareness",
            conversion_score=0.20,
            avatar_id="avatar-456",
        )

        top_hooks = engine.top_hook_patterns(persona_id="avatar-123")
        assert len(top_hooks) == 1
        assert top_hooks[0]["pattern"] == "persona_hook"

    def test_5_records_trigger_boost(self, engine):
        """Records >= _BOOST_MIN_RECORDS (3) should trigger adaptive boost."""
        for i in range(5):
            engine.record(
                video_id=f"boost-vid-{i}",
                hook_pattern="boost_hook",
                cta_pattern="boost_cta",
                template_family="boost_family",
                conversion_score=0.80,
            )

        score = engine.adaptive_score(
            template_family="boost_family",
            hook_pattern="boost_hook",
        )
        # Score should be above the base 0.5
        assert score > 0.5, f"Expected score > 0.5, got {score}"


class TestExperimentWinnerInjector:
    def test_inject_writes_calibration(self, engine, db_session):
        """ExperimentWinnerInjector should upsert a ScoringCalibration row."""
        from app.services.experiment_winner_injector import ExperimentWinnerInjector

        experiment_id = "exp-injector-001"
        _inject_records(engine, experiment_id)

        # Minimal channel_engine mock
        class _FakeChannelEngine:
            _adaptive_weight_adjustments: dict = {}

        injector = ExperimentWinnerInjector()
        result = injector.inject(
            db=db_session,
            learning_store=engine,
            experiment_id=experiment_id,
            channel_engine=_FakeChannelEngine(),
        )
        assert result["injected"] is True
        assert result["winner_variant_id"] == "variant-A"

    def test_inject_no_data_returns_no_injection(self, engine, db_session):
        from app.services.experiment_winner_injector import ExperimentWinnerInjector

        class _FakeChannelEngine:
            _adaptive_weight_adjustments: dict = {}

        injector = ExperimentWinnerInjector()
        result = injector.inject(
            db=db_session,
            learning_store=engine,
            experiment_id="non-existent-exp",
            channel_engine=_FakeChannelEngine(),
        )
        assert result["injected"] is False
