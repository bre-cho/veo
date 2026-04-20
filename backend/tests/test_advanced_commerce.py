from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.commerce.cta_engine import CTAEngine
from app.services.commerce.hook_engine import HookEngine
from app.services.commerce.extended_review_engine import (
    ComparisonVideoEngine,
    TestimonialVideoEngine,
)
from app.services.commerce.combo_recommender import AvatarTemplateComboRecommender
from app.services.analytics_action_service import AnalyticsActionService
from app.services.learning_engine import PerformanceLearningEngine

client = TestClient(app)
_hook_engine = HookEngine()
_cta_engine = CTAEngine()
_testimonial_engine = TestimonialVideoEngine()
_comparison_engine = ComparisonVideoEngine()
_combo_recommender = AvatarTemplateComboRecommender()
_analytics_svc = AnalyticsActionService()


# ---------------------------------------------------------------------------
# HookEngine unit tests
# ---------------------------------------------------------------------------

def test_hook_generate_returns_string() -> None:
    hook = _hook_engine.generate(
        template_type="review",
        product_name="SpeedApp",
        pain_hint="slow workflows",
        target_audience="developer",
    )
    assert isinstance(hook, str)
    assert hook.strip() != ""


def test_hook_generate_all_returns_list() -> None:
    variants = _hook_engine.generate_all(
        template_type="viral",
        product_name="FlowTool",
        pain_hint="context switching",
        target_audience="freelancer",
    )
    assert isinstance(variants, list)
    assert len(variants) > 0
    assert all(isinstance(v, str) for v in variants)


def test_hook_unknown_template_type_uses_defaults() -> None:
    hook = _hook_engine.generate(
        template_type="unknown_type",
        product_name="TestProduct",
        pain_hint="something",
        target_audience="someone",
    )
    assert "TestProduct" in hook or "something" in hook


def test_hook_variant_index_cycles() -> None:
    hooks = [
        _hook_engine.generate(
            template_type="testimonial",
            product_name="X",
            pain_hint="Y",
            target_audience="Z",
            variant_index=i,
        )
        for i in range(10)
    ]
    # They should cycle (not all identical but no crash)
    assert all(isinstance(h, str) for h in hooks)


def test_hook_supported_types() -> None:
    types = HookEngine.supported_template_types()
    assert "review" in types
    assert "testimonial" in types
    assert "comparison" in types


# ---------------------------------------------------------------------------
# CTAEngine unit tests
# ---------------------------------------------------------------------------

def test_cta_generate_returns_string() -> None:
    cta = _cta_engine.generate(
        intent="urgency",
        product_name="TaskMaster",
        target_audience="manager",
    )
    assert isinstance(cta, str)
    assert "TaskMaster" in cta or "manager" in cta


def test_cta_generate_all_has_variants() -> None:
    variants = _cta_engine.generate_all(
        intent="discount",
        product_name="BudgetApp",
        target_audience="student",
    )
    assert len(variants) >= 3
    assert all(isinstance(v, str) for v in variants)


def test_cta_bundle_has_all_intents() -> None:
    bundle = _cta_engine.generate_bundle(
        product_name="SalesPro",
        target_audience="salesperson",
    )
    for intent in CTAEngine.supported_intents():
        assert intent in bundle
        assert isinstance(bundle[intent], str)


def test_cta_unknown_intent_uses_default() -> None:
    cta = _cta_engine.generate(
        intent="totally_unknown",
        product_name="Prod",
        target_audience="user",
    )
    assert isinstance(cta, str)
    assert cta.strip() != ""


# ---------------------------------------------------------------------------
# TestimonialVideoEngine unit tests
# ---------------------------------------------------------------------------

def test_testimonial_generates_script() -> None:
    script = _testimonial_engine.generate(
        product_name="GrowthKit",
        product_features=["automated outreach", "AI scoring"],
        target_audience="sales rep",
    )
    assert script.product_name == "GrowthKit"
    assert script.hook.strip() != ""
    assert script.cta.strip() != ""
    assert len(script.scenes) >= 5


def test_testimonial_has_hook_and_cta_scenes() -> None:
    script = _testimonial_engine.generate(
        product_name="EduPro",
        product_features=["quiz builder"],
        target_audience="teacher",
        conversion_mode="urgency",
    )
    roles = [s.scene_role for s in script.scenes]
    assert "hook" in roles
    assert "cta" in roles


def test_testimonial_scene_templates_tagged() -> None:
    script = _testimonial_engine.generate(
        product_name="FitTracker",
        product_features=["sleep tracking"],
        target_audience="athlete",
    )
    for s in script.scenes:
        assert s.metadata.get("template") == "testimonial"


def test_testimonial_conversion_score_in_range() -> None:
    script = _testimonial_engine.generate(
        product_name="ShopBot",
        product_features=["auto replies"],
        target_audience="retailer",
    )
    assert 0.0 <= script.conversion_score <= 1.0


# ---------------------------------------------------------------------------
# ComparisonVideoEngine unit tests
# ---------------------------------------------------------------------------

def test_comparison_generates_script() -> None:
    script = _comparison_engine.generate(
        product_name="NewTool",
        competitor_name="OldTool",
        product_features=["faster sync", "AI assistance"],
        target_audience="designer",
    )
    assert script.product_name == "NewTool"
    assert "OldTool" in script.body
    assert len(script.scenes) >= 5


def test_comparison_has_hook_and_cta() -> None:
    script = _comparison_engine.generate(
        product_name="Alpha",
        competitor_name="Beta",
        product_features=["one-click deploy"],
        target_audience="dev",
    )
    roles = [s.scene_role for s in script.scenes]
    assert "hook" in roles
    assert "cta" in roles


def test_comparison_feature_scenes_appear() -> None:
    script = _comparison_engine.generate(
        product_name="CloudX",
        competitor_name="CloudY",
        product_features=["cost reduction", "better uptime", "24/7 support"],
        target_audience="CTO",
    )
    roles = [s.scene_role for s in script.scenes]
    # 3 features → 3 benefit scenes
    benefit_count = sum(1 for r in roles if r == "benefit")
    assert benefit_count == 3


def test_comparison_templates_tagged() -> None:
    script = _comparison_engine.generate(
        product_name="P",
        competitor_name="Q",
        product_features=["feature"],
        target_audience="buyer",
    )
    for s in script.scenes:
        assert s.metadata.get("template") == "comparison"


# ---------------------------------------------------------------------------
# AvatarTemplateComboRecommender unit tests
# ---------------------------------------------------------------------------

def test_combo_recommend_returns_combo() -> None:
    combo = _combo_recommender.recommend(
        content_goal="sales",
        market_code="en-US",
        conversion_mode="urgency",
    )
    assert combo.template_family != ""
    assert combo.cta_intent != ""
    assert combo.style_preset != ""
    assert 0.0 <= combo.estimated_conversion_score <= 1.0


def test_combo_recommend_with_candidates() -> None:
    candidates = [
        {"id": "av-01", "name": "Alex", "market_code": "en-US"},
        {"id": "av-02", "name": "Sam", "market_code": "vi-VN"},
    ]
    combo = _combo_recommender.recommend(
        content_goal="lead_generation",
        market_code="en-US",
        candidate_avatars=candidates,
    )
    assert combo.avatar_id == "av-01"
    assert combo.avatar_name == "Alex"


def test_combo_recommend_no_market() -> None:
    combo = _combo_recommender.recommend(content_goal="education")
    assert combo.template_family != ""


# ---------------------------------------------------------------------------
# AnalyticsActionService unit tests
# ---------------------------------------------------------------------------

def test_analytics_action_suggests_hook_change_when_weak() -> None:
    actions = _analytics_svc.suggest(
        conversion_score=0.6,
        details={"hook_strength": 0, "clarity": 2, "cta_presence": 3},
        content_goal="sales",
    )
    action_types = [a["action"] for a in actions]
    assert "change_hook" in action_types


def test_analytics_action_suggests_cta_change_when_weak() -> None:
    actions = _analytics_svc.suggest(
        conversion_score=0.6,
        details={"hook_strength": 2, "clarity": 2, "cta_presence": 0},
        content_goal="lead_generation",
    )
    action_types = [a["action"] for a in actions]
    assert "change_cta" in action_types


def test_analytics_action_template_change_when_clarity_low() -> None:
    actions = _analytics_svc.suggest(
        conversion_score=0.5,
        details={"hook_strength": 2, "clarity": 0, "cta_presence": 2},
        current_template_family="viral_clip",
    )
    action_types = [a["action"] for a in actions]
    assert "change_template" in action_types


def test_analytics_action_comprehensive_when_very_low_score() -> None:
    actions = _analytics_svc.suggest(
        conversion_score=0.2,
        details={"hook_strength": 2, "clarity": 2, "cta_presence": 2},
    )
    action_types = [a["action"] for a in actions]
    assert "comprehensive_review" in action_types


def test_analytics_action_high_priority_first() -> None:
    actions = _analytics_svc.suggest(
        conversion_score=0.3,
        details={"hook_strength": 0, "clarity": 0, "cta_presence": 0},
    )
    if len(actions) > 1:
        assert actions[0]["priority"] in ("high", "medium")


def test_analytics_from_score_result() -> None:
    score_result = {
        "conversion_score": 0.4,
        "details": {"hook_strength": 1, "clarity": 1, "cta_presence": 1},
    }
    actions = _analytics_svc.suggest_from_score_result(
        score_result, content_goal="sales"
    )
    assert isinstance(actions, list)


# ---------------------------------------------------------------------------
# PerformanceLearningEngine unit tests
# ---------------------------------------------------------------------------

def test_learning_engine_record_and_retrieve(tmp_path) -> None:
    engine = PerformanceLearningEngine(store_path=str(tmp_path / "store.json"))
    engine.record(
        video_id="vid-1",
        hook_pattern="Struggling with X?",
        cta_pattern="Shop now",
        template_family="sales_conversion",
        conversion_score=0.8,
        view_count=1000,
        click_through_rate=0.05,
    )
    records = engine.all_records()
    assert len(records) == 1
    assert records[0]["video_id"] == "vid-1"


def test_learning_engine_upsert(tmp_path) -> None:
    engine = PerformanceLearningEngine(store_path=str(tmp_path / "store.json"))
    engine.record(
        video_id="vid-1",
        hook_pattern="Hook A",
        cta_pattern="CTA A",
        template_family="product_review",
        conversion_score=0.5,
    )
    engine.record(
        video_id="vid-1",
        hook_pattern="Hook A Updated",
        cta_pattern="CTA A",
        template_family="product_review",
        conversion_score=0.9,
    )
    records = engine.all_records()
    assert len(records) == 1
    assert records[0]["hook_pattern"] == "Hook A Updated"


def test_learning_engine_top_patterns(tmp_path) -> None:
    engine = PerformanceLearningEngine(store_path=str(tmp_path / "store.json"))
    engine.record(
        video_id="v1", hook_pattern="Hook A", cta_pattern="CTA X",
        template_family="sales_conversion", conversion_score=0.9
    )
    engine.record(
        video_id="v2", hook_pattern="Hook B", cta_pattern="CTA X",
        template_family="product_review", conversion_score=0.5
    )
    top = engine.top_hook_patterns(limit=2)
    assert top[0]["pattern"] == "Hook A"
    assert top[0]["avg_score"] == 0.9


def test_learning_engine_summary_empty(tmp_path) -> None:
    engine = PerformanceLearningEngine(store_path=str(tmp_path / "store.json"))
    summary = engine.feedback_summary()
    assert summary["total_records"] == 0
    assert summary["avg_conversion_score"] == 0.0


def test_learning_engine_summary_with_records(tmp_path) -> None:
    engine = PerformanceLearningEngine(store_path=str(tmp_path / "store.json"))
    for i in range(3):
        engine.record(
            video_id=f"v{i}",
            hook_pattern=f"Hook {i}",
            cta_pattern="CTA",
            template_family="sales_conversion",
            conversion_score=float(i) / 3,
        )
    summary = engine.feedback_summary()
    assert summary["total_records"] == 3
    assert 0.0 <= summary["avg_conversion_score"] <= 1.0


# ---------------------------------------------------------------------------
# API endpoint tests for new routes
# ---------------------------------------------------------------------------

def test_api_generate_cta_urgency() -> None:
    resp = client.post(
        "/api/v1/commerce/generate-cta",
        json={
            "intent": "urgency",
            "product_name": "Flash",
            "target_audience": "shopper",
            "deadline": "tonight",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "urgency"
    assert data["cta_text"].strip() != ""


def test_api_generate_cta_all_variants() -> None:
    resp = client.post(
        "/api/v1/commerce/generate-cta",
        json={
            "intent": "discount",
            "product_name": "DealApp",
            "target_audience": "buyer",
            "all_variants": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["variants"]) > 0


def test_api_generate_hook_review() -> None:
    resp = client.post(
        "/api/v1/commerce/generate-hook",
        json={
            "template_type": "review",
            "product_name": "TestKit",
            "pain_hint": "slow testing",
            "target_audience": "developer",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_type"] == "review"
    assert data["hook_text"].strip() != ""


def test_api_generate_hook_all_variants() -> None:
    resp = client.post(
        "/api/v1/commerce/generate-hook",
        json={
            "template_type": "viral",
            "product_name": "Boom",
            "pain_hint": "motivation",
            "target_audience": "creator",
            "all_variants": True,
        },
    )
    assert resp.status_code == 200
    assert len(resp.json()["variants"]) > 0


def test_api_generate_testimonial_video() -> None:
    resp = client.post(
        "/api/v1/commerce/generate-testimonial-video",
        json={
            "product_name": "TrustBridge",
            "product_features": ["real-time sync", "smart alerts"],
            "target_audience": "ops manager",
            "conversion_mode": "soft",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["product_name"] == "TrustBridge"
    assert len(data["scenes"]) >= 5
    assert 0.0 <= data["conversion_score_result"]["conversion_score"] <= 1.0


def test_api_generate_comparison_video() -> None:
    resp = client.post(
        "/api/v1/commerce/generate-comparison-video",
        json={
            "product_name": "NewApp",
            "competitor_name": "OldApp",
            "product_features": ["feature1", "feature2"],
            "target_audience": "entrepreneur",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["product_name"] == "NewApp"
    assert len(data["scenes"]) >= 5


def test_api_template_intelligence() -> None:
    resp = client.post(
        "/api/v1/commerce/template-intelligence",
        json={"content_goal": "sales", "market_code": "vi-VN"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_family"] != ""
    assert data["style_preset"] != ""
    assert data["cta_intent"] != ""
    assert data["recommended_scene_count"] > 0


def test_api_recommend_combo() -> None:
    resp = client.post(
        "/api/v1/commerce/recommend-combo",
        json={
            "content_goal": "lead_generation",
            "market_code": "en-US",
            "conversion_mode": "urgency",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_family"] != ""
    assert 0.0 <= data["estimated_conversion_score"] <= 1.0


def test_api_analytics_action_weak_hook() -> None:
    resp = client.post(
        "/api/v1/commerce/analytics-action",
        json={
            "conversion_score": 0.55,
            "details": {"hook_strength": 0, "clarity": 2, "cta_presence": 3},
            "content_goal": "sales",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["suggestion_count"] > 0
    action_types = [a["action"] for a in data["actions"]]
    assert "change_hook" in action_types


def test_api_learning_record_and_summary() -> None:
    resp = client.post(
        "/api/v1/commerce/learning/record",
        json={
            "video_id": "test-vid-999",
            "hook_pattern": "Did you know?",
            "cta_pattern": "Shop now",
            "template_family": "sales_conversion",
            "conversion_score": 0.75,
            "view_count": 5000,
            "click_through_rate": 0.08,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    resp_summary = client.get("/api/v1/commerce/learning/summary")
    assert resp_summary.status_code == 200
    summary = resp_summary.json()
    assert summary["total_records"] >= 1
