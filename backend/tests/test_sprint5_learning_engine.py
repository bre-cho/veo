"""Sprint 5 – Learning Engine adaptive scoring + event schema tests.

Covers:
- Extended event schema: avatar_id, product_id, experiment_id, variant_id,
  performance_metrics all stored in record
- record_experiment(): deterministic IDs, stored correctly
- experiment_summary(): aggregates by variant, identifies winner
- adaptive_score(): base + performance_boost logic, min records guard
- Backward compatibility: original record() signature still works
"""
from __future__ import annotations

import pytest

from app.services.learning_engine import PerformanceLearningEngine, _ADAPTIVE_BASE_SCORE


# Use isolated in-memory store for each test (no file I/O)
def _fresh_engine() -> PerformanceLearningEngine:
    return PerformanceLearningEngine(store_path="/dev/null")


# ---------------------------------------------------------------------------
# Extended event schema
# ---------------------------------------------------------------------------

def test_record_stores_avatar_and_product_ids() -> None:
    eng = _fresh_engine()
    rec = eng.record(
        video_id="v1",
        hook_pattern="Did you know?",
        cta_pattern="Buy now",
        template_family="testimonial",
        conversion_score=0.8,
        avatar_id="av1",
        product_id="prod1",
    )
    assert rec["avatar_id"] == "av1"
    assert rec["product_id"] == "prod1"


def test_record_stores_performance_metrics() -> None:
    eng = _fresh_engine()
    metrics = {"retention_rate": 0.65, "share_rate": 0.12}
    rec = eng.record(
        video_id="v2",
        hook_pattern="Stop wasting money",
        cta_pattern="Start free trial",
        template_family="comparison",
        conversion_score=0.75,
        performance_metrics=metrics,
    )
    assert rec["performance_metrics"] == metrics


def test_record_stores_experiment_and_variant_ids() -> None:
    eng = _fresh_engine()
    rec = eng.record(
        video_id="v3",
        hook_pattern="hook",
        cta_pattern="cta",
        template_family="review",
        conversion_score=0.6,
        experiment_id="exp-abc",
        variant_id="var-a",
    )
    assert rec["experiment_id"] == "exp-abc"
    assert rec["variant_id"] == "var-a"


def test_backward_compat_record_without_new_fields() -> None:
    """Original record() call without Sprint 5 fields must still work."""
    eng = _fresh_engine()
    rec = eng.record(
        video_id="v4",
        hook_pattern="hook",
        cta_pattern="cta",
        template_family="review",
        conversion_score=0.55,
    )
    assert rec["video_id"] == "v4"
    # New fields should default to None / empty
    assert rec.get("avatar_id") is None
    assert rec.get("experiment_id") is None
    assert rec.get("performance_metrics") == {}


# ---------------------------------------------------------------------------
# record_experiment()
# ---------------------------------------------------------------------------

def test_record_experiment_generates_stable_ids() -> None:
    eng = _fresh_engine()
    rec1 = eng.record_experiment(
        experiment_name="hook_ab_test",
        variant_name="variant_A",
        video_id="v10",
        hook_pattern="hook A",
        cta_pattern="cta",
        template_family="review",
        conversion_score=0.7,
    )
    rec2 = eng.record_experiment(
        experiment_name="hook_ab_test",
        variant_name="variant_A",
        video_id="v11",
        hook_pattern="hook A",
        cta_pattern="cta",
        template_family="review",
        conversion_score=0.72,
    )
    # Same experiment name → same experiment_id
    assert rec1["experiment_id"] == rec2["experiment_id"]
    # Same variant name → same variant_id
    assert rec1["variant_id"] == rec2["variant_id"]


def test_record_experiment_different_variants_have_different_ids() -> None:
    eng = _fresh_engine()
    r_a = eng.record_experiment(
        experiment_name="cta_test",
        variant_name="variant_A",
        video_id="v20",
        hook_pattern="hook",
        cta_pattern="cta A",
        template_family="review",
        conversion_score=0.6,
    )
    r_b = eng.record_experiment(
        experiment_name="cta_test",
        variant_name="variant_B",
        video_id="v21",
        hook_pattern="hook",
        cta_pattern="cta B",
        template_family="review",
        conversion_score=0.8,
    )
    assert r_a["variant_id"] != r_b["variant_id"]
    assert r_a["experiment_id"] == r_b["experiment_id"]


# ---------------------------------------------------------------------------
# experiment_summary()
# ---------------------------------------------------------------------------

def _seed_experiment(eng: PerformanceLearningEngine) -> str:
    """Seed experiment data and return experiment_name."""
    exp = "test_exp_winner"
    for i, (vid, score, variant) in enumerate([
        ("v30", 0.5, "low"),
        ("v31", 0.55, "low"),
        ("v32", 0.9, "high"),
        ("v33", 0.85, "high"),
        ("v34", 0.88, "high"),
    ]):
        eng.record_experiment(
            experiment_name=exp,
            variant_name=variant,
            video_id=vid,
            hook_pattern="h",
            cta_pattern="c",
            template_family="fam",
            conversion_score=score,
        )
    return exp


def test_experiment_summary_identifies_winner() -> None:
    eng = _fresh_engine()
    exp = _seed_experiment(eng)
    summary = eng.experiment_summary(experiment_name=exp)
    assert summary["winner_variant_id"] is not None
    # Winner should be "high" variant (avg ~0.88)
    winner = summary["winner_variant_id"]
    assert summary["variants"][0]["avg_score"] >= 0.8


def test_experiment_summary_by_id() -> None:
    import uuid
    eng = _fresh_engine()
    exp_name = "exp_by_id"
    exp_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"exp:{exp_name}"))
    eng.record_experiment(
        experiment_name=exp_name,
        variant_name="A",
        video_id="v40",
        hook_pattern="h",
        cta_pattern="c",
        template_family="fam",
        conversion_score=0.7,
    )
    summary = eng.experiment_summary(experiment_id=exp_id)
    assert len(summary["variants"]) >= 1


def test_experiment_summary_empty_for_unknown_experiment() -> None:
    eng = _fresh_engine()
    summary = eng.experiment_summary(experiment_id="non-existent-exp-id")
    assert summary["variants"] == []
    assert summary["winner_variant_id"] is None


# ---------------------------------------------------------------------------
# adaptive_score()  –  base + performance_boost
# ---------------------------------------------------------------------------

def test_adaptive_score_returns_base_when_no_records() -> None:
    eng = _fresh_engine()
    score = eng.adaptive_score(template_family="testimonial")
    assert score == pytest.approx(_ADAPTIVE_BASE_SCORE, abs=0.01)


def test_adaptive_score_boosted_above_base_for_high_performers() -> None:
    eng = _fresh_engine()
    for i in range(5):
        eng.record(
            video_id=f"high_{i}",
            hook_pattern="hook",
            cta_pattern="cta",
            template_family="comparison",
            conversion_score=0.9,
            platform="tiktok",
        )
    score = eng.adaptive_score(template_family="comparison", platform="tiktok")
    assert score > _ADAPTIVE_BASE_SCORE


def test_adaptive_score_penalised_below_base_for_low_performers() -> None:
    eng = _fresh_engine()
    for i in range(5):
        eng.record(
            video_id=f"low_{i}",
            hook_pattern="hook",
            cta_pattern="cta",
            template_family="low_fam",
            conversion_score=0.1,
        )
    score = eng.adaptive_score(template_family="low_fam")
    assert score < _ADAPTIVE_BASE_SCORE


def test_adaptive_score_different_template_families_differ() -> None:
    eng = _fresh_engine()
    for i in range(5):
        eng.record(
            video_id=f"top_{i}",
            hook_pattern="h",
            cta_pattern="c",
            template_family="top",
            conversion_score=0.95,
        )
        eng.record(
            video_id=f"bot_{i}",
            hook_pattern="h",
            cta_pattern="c",
            template_family="bottom",
            conversion_score=0.1,
        )
    top_score = eng.adaptive_score(template_family="top")
    bot_score = eng.adaptive_score(template_family="bottom")
    assert top_score > bot_score


def test_adaptive_score_clamped_to_unit_interval() -> None:
    eng = _fresh_engine()
    for i in range(10):
        eng.record(
            video_id=f"max_{i}",
            hook_pattern="h",
            cta_pattern="c",
            template_family="perfect",
            conversion_score=1.0,
        )
    score = eng.adaptive_score(template_family="perfect")
    assert 0.0 <= score <= 1.0
