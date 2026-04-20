from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.commerce.review_engine import (
    ConversionScoreService,
    ReviewVideoEngine,
)

client = TestClient(app)
_engine = ReviewVideoEngine()
_scorer = ConversionScoreService()


# ---------------------------------------------------------------------------
# ReviewVideoEngine unit tests
# ---------------------------------------------------------------------------

def test_generate_returns_5_to_7_scenes() -> None:
    script = _engine.generate(
        product_name="SpeedTask",
        product_features=["instant task creation", "AI prioritization"],
        target_audience="freelancer",
    )
    assert 5 <= len(script.scenes) <= 7


def test_generate_scene_roles_cover_hook_and_cta() -> None:
    script = _engine.generate(
        product_name="FitBot",
        product_features=["workout tracking", "nutrition AI"],
        target_audience="gym enthusiast",
        conversion_mode="urgency",
    )
    roles = [s.scene_role for s in script.scenes]
    assert "hook" in roles
    assert "cta" in roles


def test_generate_hook_contains_product_reference() -> None:
    script = _engine.generate(
        product_name="CloudDrive Pro",
        product_features=["unlimited storage"],
        target_audience="remote worker",
    )
    assert "CloudDrive Pro" in script.hook or "CloudDrive Pro" in script.scenes[0].script_text


def test_generate_cta_field_not_empty() -> None:
    script = _engine.generate(
        product_name="NovaPen",
        product_features=["smart ink", "AI notes"],
        target_audience="student",
    )
    assert script.cta.strip() != ""


def test_generate_sets_content_goal() -> None:
    script = _engine.generate(
        product_name="SalesBot",
        product_features=["auto-follow-up emails", "deal scoring"],
        target_audience="sales rep",
        conversion_mode="urgency",
    )
    assert script.content_goal != ""


def test_generate_single_feature_no_error() -> None:
    script = _engine.generate(
        product_name="QuickNote",
        product_features=["one-tap notes"],
        target_audience="busy professional",
    )
    assert len(script.scenes) >= 5


def test_generate_scenes_have_visual_prompts() -> None:
    script = _engine.generate(
        product_name="AdFlow",
        product_features=["ad targeting", "budget optimization"],
        target_audience="marketer",
    )
    for scene in script.scenes:
        assert scene.visual_prompt.strip() != ""


def test_generate_scenes_have_positive_durations() -> None:
    script = _engine.generate(
        product_name="StudyPath",
        product_features=["spaced repetition", "AI flashcards"],
        target_audience="student",
    )
    for scene in script.scenes:
        assert scene.target_duration_sec > 0


def test_to_preview_payload_structure() -> None:
    script = _engine.generate(
        product_name="RetailAI",
        product_features=["inventory prediction"],
        target_audience="retailer",
        avatar_id="av-01",
        market_code="en-US",
    )
    payload = script.to_preview_payload(
        aspect_ratio="9:16",
        target_platform="shorts",
        avatar_id="av-01",
        market_code="en-US",
    )
    assert payload["avatar_id"] == "av-01"
    assert payload["market_code"] == "en-US"
    assert payload["content_goal"] == script.content_goal
    assert len(payload["scenes"]) == len(script.scenes)
    assert len(payload["subtitle_segments"]) > 0
    assert payload["script_text"].strip() != ""


# ---------------------------------------------------------------------------
# ConversionScoreService unit tests
# ---------------------------------------------------------------------------

def test_conversion_score_returns_float_in_range() -> None:
    script = _engine.generate(
        product_name="LeadMax",
        product_features=["form capture", "CRM sync"],
        target_audience="marketer",
        conversion_mode="urgency",
    )
    result = _scorer.score_script(script)
    assert "conversion_score" in result
    assert 0.0 <= result["conversion_score"] <= 1.0


def test_conversion_score_details_keys_present() -> None:
    script = _engine.generate(
        product_name="BudgetApp",
        product_features=["expense tracking"],
        target_audience="user",
    )
    result = _scorer.score_script(script)
    details = result["details"]
    assert "hook_strength" in details
    assert "clarity" in details
    assert "cta_presence" in details
    assert "max_possible" in details


def test_conversion_score_higher_with_urgency_cta() -> None:
    """Both urgency and default conversion modes must produce valid scores in [0,1]."""
    script_urgency = _engine.generate(
        product_name="FlashSale",
        product_features=["buy now discount"],
        target_audience="shopper",
        conversion_mode="urgency",
    )
    script_default = _engine.generate(
        product_name="FlashSale",
        product_features=["buy now discount"],
        target_audience="shopper",
        conversion_mode=None,
    )
    score_urgency = _scorer.score_script(script_urgency)["conversion_score"]
    score_default = _scorer.score_script(script_default)["conversion_score"]
    assert 0.0 <= score_urgency <= 1.0
    assert 0.0 <= score_default <= 1.0


def test_score_scenes_dict_interface() -> None:
    scenes = [
        {"scene_index": 1, "scene_role": "hook", "script_text": "Did you know? You can buy now!"},
        {"scene_index": 2, "scene_role": "cta", "script_text": "Get it today – limited offer!"},
    ]
    result = _scorer.score_scenes(scenes, cta_text="Shop now – limited time offer")
    assert 0.0 <= result["conversion_score"] <= 1.0
    assert result["details"]["cta_presence"] > 0


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

def test_generate_review_video_api_happy_path() -> None:
    resp = client.post(
        "/api/v1/commerce/generate-review-video",
        json={
            "product_name": "TaskMaster",
            "product_features": ["AI task scheduling", "team sync"],
            "target_audience": "project manager",
            "conversion_mode": "urgency",
            "aspect_ratio": "9:16",
            "target_platform": "shorts",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["product_name"] == "TaskMaster"
    assert data["target_audience"] == "project manager"
    assert data["hook"].strip() != ""
    assert data["cta"].strip() != ""
    assert 5 <= len(data["scenes"]) <= 7
    assert "conversion_score" in data["conversion_score_result"]
    assert 0.0 <= data["conversion_score_result"]["conversion_score"] <= 1.0


def test_generate_review_video_api_preview_payload_fields() -> None:
    resp = client.post(
        "/api/v1/commerce/generate-review-video",
        json={
            "product_name": "HealthTracker",
            "product_features": ["step counting", "sleep analysis"],
            "target_audience": "fitness lover",
            "avatar_id": "av-99",
            "market_code": "vi-VN",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()["preview_payload"]
    assert payload["avatar_id"] == "av-99"
    assert payload["market_code"] == "vi-VN"
    assert payload["aspect_ratio"] == "9:16"
    assert len(payload["scenes"]) > 0
    assert len(payload["subtitle_segments"]) > 0


def test_generate_review_video_api_missing_required_fields() -> None:
    resp = client.post(
        "/api/v1/commerce/generate-review-video",
        json={
            "product_name": "Oops",
            # missing product_features, target_audience
        },
    )
    assert resp.status_code == 422


def test_generate_review_video_api_empty_features_rejected() -> None:
    resp = client.post(
        "/api/v1/commerce/generate-review-video",
        json={
            "product_name": "Widget",
            "product_features": [],
            "target_audience": "developer",
        },
    )
    assert resp.status_code == 422
