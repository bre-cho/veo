from __future__ import annotations

from app.services.commerce.review_variant_engine import ReviewVariantEngine


def _profile() -> dict:
    return {
        "product_name": "FocusKit",
        "benefits": ["faster content output"],
        "pain_points": ["slow scripting"],
        "social_proof": ["used by 10k creators"],
        "target_audience": "creator",
        "market_code": "en-US",
    }


def test_create_at_least_three_variants() -> None:
    engine = ReviewVariantEngine()
    variants = engine.generate_variants(_profile(), count=4)
    assert len(variants) >= 3


def test_each_variant_has_score() -> None:
    engine = ReviewVariantEngine()
    variants = engine.generate_variants(_profile(), count=4)
    assert all("score" in v for v in variants)


def test_winner_selection_not_empty() -> None:
    engine = ReviewVariantEngine()
    variants = engine.generate_variants(_profile(), count=4)
    winner = engine.select_winner(variants)
    assert winner
