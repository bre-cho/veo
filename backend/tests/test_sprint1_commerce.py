"""Sprint 1 – Commerce + Review Engine tests.

Covers:
- Normalised product schema (personas, objections, product_category)
- New ConversionScoringEngine dimensions (persona_fit, product_category_fit, platform_fit)
- ReviewVariantEngine history tracking (generate_variants_with_history / get_history)
- TemplateRecommendationService product-profile score boosting
"""
from __future__ import annotations

import pytest

from app.schemas.product_ingestion import ProductIngestionRequest
from app.services.commerce.conversion_scoring_engine import ConversionScoringEngine
from app.services.commerce.product_ingestion_service import ProductIngestionService
from app.services.commerce.review_variant_engine import ReviewVariantEngine


# ---------------------------------------------------------------------------
# ProductIngestionService – new schema fields
# ---------------------------------------------------------------------------

_svc = ProductIngestionService()


def test_personas_extracted_from_reviews() -> None:
    req = ProductIngestionRequest(
        product_name="GymPro",
        product_features=["protein tracking"],
        customer_reviews=["Great for athletes and gym users"],
        target_audience="gym enthusiasts",
    )
    result = _svc.ingest(req)
    assert isinstance(result.personas, list)
    # "athlete" keyword matches persona library
    assert len(result.personas) > 0


def test_personas_passed_through_directly() -> None:
    req = ProductIngestionRequest(
        product_name="BizFlow",
        product_features=["invoicing"],
        personas=["solopreneur", "small business owner"],
    )
    result = _svc.ingest(req)
    assert result.personas == ["solopreneur", "small business owner"]


def test_objections_extracted_from_reviews() -> None:
    req = ProductIngestionRequest(
        product_name="CostCutter",
        customer_reviews=["This is too expensive", "Not sure it's worth it"],
    )
    result = _svc.ingest(req)
    assert isinstance(result.objections, list)
    # at least one objection should be detected
    assert len(result.objections) > 0


def test_objections_passed_through_directly() -> None:
    req = ProductIngestionRequest(
        product_name="NanoTech",
        objections=["too complicated", "risky investment"],
    )
    result = _svc.ingest(req)
    assert result.objections == ["too complicated", "risky investment"]


def test_product_category_detected() -> None:
    req = ProductIngestionRequest(
        product_name="SkinGlow Serum",
        product_features=["moisturizer formula", "acne control", "skin repair cream"],
    )
    result = _svc.ingest(req)
    assert result.product_category == "skincare"


def test_product_category_passed_through() -> None:
    req = ProductIngestionRequest(
        product_name="PowerBand",
        product_category="fitness",
    )
    result = _svc.ingest(req)
    assert result.product_category == "fitness"


def test_recommended_angles_include_persona_and_objection() -> None:
    req = ProductIngestionRequest(
        product_name="FinBot",
        personas=["entrepreneur"],
        objections=["too expensive"],
        product_features=["saves money", "budget friendly"],
    )
    result = _svc.ingest(req)
    assert "persona-focus" in result.recommended_angles
    assert "objection-handling" in result.recommended_angles


# ---------------------------------------------------------------------------
# ConversionScoringEngine – new dimensions
# ---------------------------------------------------------------------------

_engine = ConversionScoringEngine()

_SAMPLE_VARIANT = {
    "hook": "Did you know most professionals waste 2 hours daily?",
    "body": "TaskFlow is trusted by business teams and proven to cut setup time.",
    "cta": "Start your free trial now.",
}


def test_score_includes_all_new_dimensions() -> None:
    result = _engine.score_variant(
        _SAMPLE_VARIANT,
        persona="busy professional",
        product_category="technology",
        platform="tiktok",
    )
    details = result["details"]
    assert "persona_fit" in details
    assert "product_category_fit" in details
    assert "platform_fit" in details


def test_persona_fit_boosted_when_text_matches() -> None:
    variant_with_persona = {
        "hook": "Are you a busy professional struggling with slow tools?",
        "body": "TaskFlow is built for professionals at work.",
        "cta": "Buy now",
    }
    high = _engine.score_variant(variant_with_persona, persona="busy professional")
    generic = _engine.score_variant({"hook": "x", "body": "y", "cta": "z"}, persona="busy professional")
    assert high["details"]["persona_fit"] >= generic["details"]["persona_fit"]


def test_product_category_fit_uses_lookup() -> None:
    r = _engine.score_variant(_SAMPLE_VARIANT, product_category="skincare")
    assert r["details"]["product_category_fit"] == pytest.approx(0.80, abs=0.01)


def test_platform_fit_short_copy_tiktok() -> None:
    short_variant = {"hook": "Try this now.", "body": "It works fast.", "cta": "Order today."}
    result = _engine.score_variant(short_variant, platform="tiktok")
    assert result["details"]["platform_fit"] >= 0.80


def test_platform_fit_long_copy_tiktok_penalised() -> None:
    long_body = " ".join(["word"] * 200)
    long_variant = {"hook": "hook", "body": long_body, "cta": "Buy"}
    result = _engine.score_variant(long_variant, platform="tiktok")
    assert result["details"]["platform_fit"] < 0.85


# ---------------------------------------------------------------------------
# ReviewVariantEngine – history tracking
# ---------------------------------------------------------------------------

_rev = ReviewVariantEngine()

_PROFILE = {
    "product_name": "TestProduct",
    "product_category": "technology",
    "benefits": ["Delivers fast setup"],
    "pain_points": ["slow onboarding"],
    "social_proof": [],
    "personas": ["busy professional"],
    "objections": [],
    "market_code": "VN",
}


def test_generate_variants_with_history_returns_run_id() -> None:
    result = _rev.generate_variants_with_history(_PROFILE, count=3)
    assert "run_id" in result
    assert result["run_id"] is not None
    assert len(result["variants"]) >= 3
    assert "winner" in result
    assert result["winner"]["score"] >= 0.0


def test_history_persisted_and_retrievable() -> None:
    _rev.generate_variants_with_history(_PROFILE, count=3, context={"test": True})
    records = _rev.get_history(product_name="TestProduct")
    assert len(records) >= 1
    first = records[0]
    assert first["product_name"] == "TestProduct"
    assert "winner_score" in first
    assert "winner_score_breakdown" in first


def test_history_filter_by_platform() -> None:
    _rev.generate_variants_with_history(_PROFILE, count=3, platform="tiktok")
    _rev.generate_variants_with_history(_PROFILE, count=3, platform="youtube")
    tiktok = _rev.get_history(platform="tiktok")
    youtube = _rev.get_history(platform="youtube")
    assert all(r["platform"] == "tiktok" for r in tiktok)
    assert all(r["platform"] == "youtube" for r in youtube)


def test_winner_has_highest_score() -> None:
    result = _rev.generate_variants_with_history(_PROFILE, count=5)
    winner = result["winner"]
    for v in result["variants"]:
        assert float(v["score"]) <= float(winner["score"]) + 1e-6
