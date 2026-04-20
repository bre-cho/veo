from __future__ import annotations

import pytest

from app.services.template_intelligence import TemplateIntelligenceService

_svc = TemplateIntelligenceService()


def test_known_goal_maps_to_correct_family() -> None:
    assert _svc.get_template_family("sales") == "sales_conversion"
    assert _svc.get_template_family("education") == "how_to"
    assert _svc.get_template_family("testimonial") == "testimonial"
    assert _svc.get_template_family("brand_awareness") == "brand_story"


def test_unknown_goal_falls_back_to_default() -> None:
    family = _svc.get_template_family("unknown_goal_xyz")
    assert family == "product_review"


def test_known_market_maps_to_preset() -> None:
    assert _svc.get_style_preset("vi-VN") == "vibrant_minimal"
    assert _svc.get_style_preset("en-US") == "professional_bold"
    assert _svc.get_style_preset("ja-JP") == "clean_modern"
    assert _svc.get_style_preset("fr-FR") == "elegant_minimal"


def test_unknown_market_falls_back_to_default() -> None:
    preset = _svc.get_style_preset("xx-XX")
    assert preset == "professional_bold"


def test_language_prefix_fallback() -> None:
    # "en-ZZ" is not in the map but "en" prefix should resolve to professional_bold
    preset = _svc.get_style_preset("en-ZZ")
    assert preset == "professional_bold"


def test_empty_market_falls_back() -> None:
    preset = _svc.get_style_preset("")
    assert preset == "professional_bold"


def test_cta_intent_for_goals() -> None:
    assert _svc.get_cta_intent("sales") == "discount"
    assert _svc.get_cta_intent("conversion") == "urgency"
    assert _svc.get_cta_intent("lead_generation") == "urgency"
    assert _svc.get_cta_intent("education") == "soft"


def test_recommended_scene_count_known_family() -> None:
    assert _svc.get_recommended_scene_count("sales_conversion") == 7
    assert _svc.get_recommended_scene_count("viral_clip") == 4
    assert _svc.get_recommended_scene_count("testimonial") == 5


def test_recommended_scene_count_unknown_family() -> None:
    count = _svc.get_recommended_scene_count("unknown_family")
    assert count == 6  # default


def test_resolve_returns_full_bundle() -> None:
    result = _svc.resolve("sales", "vi-VN")
    assert result["template_family"] == "sales_conversion"
    assert result["style_preset"] == "vibrant_minimal"
    assert result["cta_intent"] == "discount"
    assert result["recommended_scene_count"] == 7


def test_resolve_without_market_uses_default_preset() -> None:
    result = _svc.resolve("education", None)
    assert result["template_family"] == "how_to"
    assert result["cta_intent"] == "soft"
    assert result["recommended_scene_count"] > 0
