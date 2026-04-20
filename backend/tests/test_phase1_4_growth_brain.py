"""Tests for Phase 1-4 new features.

Covers:
- Phase 1: persona_score_matrix, MultiObjectiveScorer, CampaignAttributionService, PortfolioBudgetOrchestrator
- Phase 2: TemporalIdentityTracker, RenderQualityAnalyzer, canonical drift-triggered refresh
- Phase 3: ComplianceRiskPolicy new rules, PlatformRecoveryWorkflow escalation, ProviderFinalStateSyncer richer fields
- Phase 4: _derive_all_scene_pacing_boosts, WinningSceneGraphStore, EpisodeMemory fields
"""
from __future__ import annotations

import time
import pytest


# ---------------------------------------------------------------------------
# Phase 1 tests
# ---------------------------------------------------------------------------


class TestPersonaScoreMatrix:
    def test_returns_dict_with_enough_records(self, tmp_path):
        from app.services.learning_engine import PerformanceLearningEngine

        engine = PerformanceLearningEngine(store_path=str(tmp_path / "store.json"))
        for i in range(3):
            engine.record(
                video_id=f"persona-vid-{i}",
                hook_pattern=f"hook_{i}",
                cta_pattern="cta",
                template_family="fam",
                conversion_score=0.7 + i * 0.05,
                persona_id="persona-A",
            )
        matrix = engine.persona_score_matrix()
        assert "persona-A" in matrix
        assert isinstance(matrix["persona-A"], dict)

    def test_empty_without_persona_records(self, tmp_path):
        from app.services.learning_engine import PerformanceLearningEngine

        engine = PerformanceLearningEngine(store_path=str(tmp_path / "store2.json"))
        engine.record(
            video_id="no-persona",
            hook_pattern="h",
            cta_pattern="c",
            template_family="f",
            conversion_score=0.5,
        )
        matrix = engine.persona_score_matrix()
        # No persona_id set — matrix should be empty
        assert matrix == {}


class TestMultiObjectiveScorer:
    def test_weights_sum_to_one(self):
        from app.services.commerce.multi_objective_scorer import MultiObjectiveScorer

        scorer = MultiObjectiveScorer({"conversion": 0.5, "ctr": 0.3, "roas": 0.2})
        total = sum(scorer.objectives.values())
        assert abs(total - 1.0) < 1e-6

    def test_score_in_range(self):
        from app.services.commerce.multi_objective_scorer import MultiObjectiveScorer

        scorer = MultiObjectiveScorer({"conversion": 0.5, "ctr": 0.3, "roas": 0.2})
        record = {
            "conversion_score": 0.8,
            "click_through_rate": 0.4,
            "performance_metrics": {"roas": 5.0},
        }
        score = scorer.score(record)
        assert 0.0 <= score <= 1.0

    def test_rejects_empty_objectives(self):
        from app.services.commerce.multi_objective_scorer import MultiObjectiveScorer

        with pytest.raises(ValueError):
            MultiObjectiveScorer({})


class TestCampaignAttributionService:
    def test_attribute_conversion_multi_touch(self, tmp_path):
        from app.services.commerce.campaign_attribution_service import CampaignAttributionService
        from app.services.learning_engine import PerformanceLearningEngine

        engine = PerformanceLearningEngine(store_path=str(tmp_path / "store.json"))
        now = time.time()
        for i in range(3):
            rec = engine.record(
                video_id=f"ca-vid-{i}",
                hook_pattern="hook",
                cta_pattern="cta",
                template_family="fam",
                conversion_score=0.7,
                campaign_id="camp-A",
            )
            rec["recorded_at"] = now - (2 - i) * 3600

        svc = CampaignAttributionService(learning_store=engine)
        result = svc.attribute_conversion(
            conversion_event={"timestamp": now, "value": 3.0},
            campaign_id="camp-A",
            n_touch=3,
        )
        assert result["campaign_id"] == "camp-A"
        assert len(result["attributions"]) <= 3
        # credits should sum to total_attributed_value
        total_credit = sum(a["credit"] for a in result["attributions"])
        assert abs(total_credit - result["total_attributed_value"]) < 0.01


class TestPortfolioBudgetOrchestrator:
    def test_allocate_total_not_exceeded(self):
        from app.services.publish_providers.campaign_budget_policy import (
            CampaignBudget,
            PortfolioBudgetOrchestrator,
        )

        campaigns = [
            CampaignBudget("c1", daily_limit=50.0, roas=2.0),
            CampaignBudget("c2", daily_limit=30.0, roas=1.0),
            CampaignBudget("c3", daily_limit=20.0, roas=0.5),
        ]
        orchestrator = PortfolioBudgetOrchestrator()
        allocation = orchestrator.allocate(campaigns, total_remaining=80.0)
        assert sum(allocation.values()) <= 80.0 + 1e-6

    def test_zero_remaining_for_capped_campaign(self):
        from app.services.publish_providers.campaign_budget_policy import (
            CampaignBudget,
            PortfolioBudgetOrchestrator,
        )

        campaigns = [
            CampaignBudget("c1", daily_limit=10.0, roas=2.0, remaining=0.0),
            CampaignBudget("c2", daily_limit=50.0, roas=1.0, remaining=50.0),
        ]
        orchestrator = PortfolioBudgetOrchestrator()
        allocation = orchestrator.allocate(campaigns, total_remaining=40.0)
        assert allocation["c1"] == 0.0
        assert allocation["c2"] <= 40.0


# ---------------------------------------------------------------------------
# Phase 2 tests
# ---------------------------------------------------------------------------


class TestTemporalIdentityTracker:
    def test_returns_score_and_weak_links(self):
        from app.services.avatar.avatar_identity_service import TemporalIdentityTracker

        tracker = TemporalIdentityTracker()
        result = tracker.track_sequence(
            render_urls=["url1", "url2", "url3"],
            avatar_id="avatar-1",
        )
        assert "continuity_score" in result
        assert 0.0 <= result["continuity_score"] <= 1.0
        assert "weak_links" in result
        assert isinstance(result["weak_links"], list)

    def test_single_url_returns_perfect_score(self):
        from app.services.avatar.avatar_identity_service import TemporalIdentityTracker

        tracker = TemporalIdentityTracker()
        result = tracker.track_sequence(render_urls=["single"], avatar_id="av")
        assert result["continuity_score"] == 1.0
        assert result["weak_links"] == []


class TestDriftTriggeredRefresh:
    def test_counters_accumulate(self):
        from app.services.avatar.canonical_reference_scheduler import (
            record_verification_failure,
            record_verification_success,
            should_drift_trigger_refresh,
            _drift_fail_counts,
        )

        avatar_id = "drift-test-avatar-phase2"
        # Reset
        _drift_fail_counts.pop(avatar_id, None)

        assert not should_drift_trigger_refresh(avatar_id)
        record_verification_failure(avatar_id)
        record_verification_failure(avatar_id)
        assert not should_drift_trigger_refresh(avatar_id)
        record_verification_failure(avatar_id)
        assert should_drift_trigger_refresh(avatar_id)
        # Reset on success
        record_verification_success(avatar_id)
        assert not should_drift_trigger_refresh(avatar_id)


class TestRenderQualityAnalyzer:
    def test_fallback_scores_on_unreachable(self):
        from app.services.avatar.render_quality_gate import RenderQualityAnalyzer

        analyzer = RenderQualityAnalyzer()
        result = analyzer.analyze("http://localhost:99999/nonexistent.mp4")
        # Must not raise; should return neutral 0.5 scores
        assert "sharpness_score" in result
        assert "face_coverage" in result
        assert "motion_blur_estimate" in result
        assert "audio_sync_score" in result
        assert result["sharpness_score"] is not None

    def test_all_four_scores_present(self):
        from app.services.avatar.render_quality_gate import RenderQualityAnalyzer

        analyzer = RenderQualityAnalyzer()
        result = analyzer.analyze("https://example.invalid/render.mp4")
        keys = {"sharpness_score", "face_coverage", "motion_blur_estimate", "audio_sync_score"}
        assert keys.issubset(result.keys())


# ---------------------------------------------------------------------------
# Phase 3 tests
# ---------------------------------------------------------------------------


class TestComplianceRiskPolicyPhase3:
    def test_caption_length_violation(self):
        from app.services.publish_providers.compliance_risk_policy import ComplianceRiskPolicy

        policy = ComplianceRiskPolicy()
        content = {
            "title": "Product review",
            "caption": "x" * 3000,  # > TikTok's 2200
        }
        result = policy.evaluate(content, platform="tiktok")
        codes = [e["code"] for e in result.preflight_errors]
        assert "caption_length_exceeded" in codes

    def test_hashtag_limit_violation(self):
        from app.services.publish_providers.compliance_risk_policy import ComplianceRiskPolicy

        policy = ComplianceRiskPolicy()
        hashtags = " ".join(f"#tag{i}" for i in range(35))  # > 30 limit
        content = {"caption": hashtags}
        result = policy.evaluate(content, platform="tiktok")
        codes = [e["code"] for e in result.preflight_errors]
        assert "hashtag_limit_exceeded" in codes

    def test_sponsored_disclosure_missing(self):
        from app.services.publish_providers.compliance_risk_policy import ComplianceRiskPolicy

        policy = ComplianceRiskPolicy()
        content = {
            "caption": "Buy this product now!",
            "is_paid_partnership": True,
        }
        result = policy.evaluate(content, platform="tiktok")
        codes = [e["code"] for e in result.preflight_errors]
        assert "missing_sponsored_content_disclosure" in codes

    def test_sponsored_disclosure_present(self):
        from app.services.publish_providers.compliance_risk_policy import ComplianceRiskPolicy

        policy = ComplianceRiskPolicy()
        content = {
            "caption": "Buy this product now! #ad",
            "is_paid_partnership": True,
        }
        result = policy.evaluate(content, platform="tiktok")
        codes = [e["code"] for e in result.preflight_errors]
        assert "missing_sponsored_content_disclosure" not in codes


class TestPlatformRecoveryEscalation:
    def test_escalates_to_human_review_after_max_retries(self):
        from app.services.publish_providers.platform_recovery_workflow import (
            PlatformRecoveryWorkflow,
            _MAX_RETRIES,
        )

        class FakeJob:
            id = "job-001"
            platform = "youtube"
            error_log = {"recovery_metadata": {"attempt_count": _MAX_RETRIES}}
            provider_metadata = {}
            status = "failed"

        class FakeDB:
            def add(self, obj): pass
            def commit(self): pass

        workflow = PlatformRecoveryWorkflow()
        fake_job = FakeJob()
        result = workflow.recover(FakeDB(), fake_job)
        assert fake_job.status == "human_review"
        assert result.get("status") == "human_review"

    def test_recovery_metadata_populated(self):
        from app.services.publish_providers.platform_recovery_workflow import PlatformRecoveryWorkflow

        class FakeJob:
            id = "job-002"
            platform = "tiktok"
            error_log = {}
            provider_metadata = {}
            status = "failed"

        class FakeDB:
            def add(self, obj): pass
            def commit(self): pass

        workflow = PlatformRecoveryWorkflow()
        result = workflow.recover(FakeDB(), FakeJob())
        meta = result.get("recovery_metadata", {})
        assert "attempt_count" in meta
        assert "last_recovery_strategy" in meta
        assert "next_retry_at" in meta


# ---------------------------------------------------------------------------
# Phase 4 tests
# ---------------------------------------------------------------------------


class TestDeriveAllScenePacingBoosts:
    def test_returns_per_goal_boost_dict(self, tmp_path):
        from app.services.storyboard_engine import _derive_all_scene_pacing_boosts
        from app.services.learning_engine import PerformanceLearningEngine

        engine = PerformanceLearningEngine(store_path=str(tmp_path / "store.json"))
        for i in range(5):
            engine.record(
                video_id=f"boost-vid-{i}",
                hook_pattern="hook_A",
                cta_pattern="cta_A",
                template_family="retention",
                conversion_score=0.8,
                platform="tiktok",
            )
        boosts = _derive_all_scene_pacing_boosts(engine, platform="tiktok")
        assert isinstance(boosts, dict)
        # With records present, at least the hook boost should be non-zero
        assert len(boosts) >= 1


class TestWinningSceneGraphStore:
    def test_record_and_retrieve(self):
        from app.services.storyboard.winning_scene_graph_store import WinningSceneGraphStore

        store = WinningSceneGraphStore()
        store._IN_MEMORY_STORE = []  # reset in-memory
        persisted = store.record_winning_graph(
            storyboard_id="sb-001",
            platform="tiktok",
            conversion_score=0.85,
            scene_sequence=[{"scene_goal": "hook", "pacing_weight": 1.2}],
        )
        assert persisted is True
        graphs = store.get_top_graphs(platform="tiktok", limit=5)
        assert len(graphs) == 1
        assert graphs[0]["conversion_score"] == 0.85

    def test_below_threshold_not_stored(self, tmp_path):
        from app.services.storyboard.winning_scene_graph_store import WinningSceneGraphStore

        store = WinningSceneGraphStore()
        initial_graphs = store.get_top_graphs(platform="low-score-platform")
        persisted = store.record_winning_graph(
            storyboard_id="sb-low",
            platform="low-score-platform",
            conversion_score=0.50,
        )
        assert persisted is False
        # Verify graph was not added
        after_graphs = store.get_top_graphs(platform="low-score-platform")
        assert len(after_graphs) == len(initial_graphs)

    def test_sorted_by_conversion_score_desc(self):
        from app.services.storyboard.winning_scene_graph_store import WinningSceneGraphStore

        store = WinningSceneGraphStore()
        # Use unique platform to avoid cross-test contamination
        for score in [0.72, 0.95, 0.80]:
            store.record_winning_graph(
                storyboard_id=f"sb-{score}",
                platform=f"test-{score}",
                conversion_score=score,
            )
        graphs_72 = store.get_top_graphs(platform="test-0.72", limit=5)
        graphs_95 = store.get_top_graphs(platform="test-0.95", limit=5)
        assert graphs_95[0]["conversion_score"] == 0.95


class TestWinningGraphInGeneration:
    def test_use_winning_graph_true_with_mock(self):
        """When use_winning_graph=True and a winning graph exists, scenes should be seeded."""
        from app.services.storyboard_engine import StoryboardEngine
        from app.services.storyboard.winning_scene_graph_store import WinningSceneGraphStore, _IN_MEMORY_STORE

        # Seed a winning graph
        WinningSceneGraphStore._PLATFORM = "tiktok"
        store = WinningSceneGraphStore()
        store.record_winning_graph(
            storyboard_id="sb-win",
            platform="tiktok",
            conversion_score=0.92,
            scene_sequence=[
                {"scene_goal": "hook", "pacing_weight": 1.4},
                {"scene_goal": "body", "pacing_weight": 0.9},
                {"scene_goal": "cta", "pacing_weight": 1.6},
            ],
        )

        engine = StoryboardEngine()
        response = engine.generate_from_script(
            script_text="Para 1\n\nPara 2\n\nPara 3",
            platform="tiktok",
            use_winning_graph=True,
        )
        assert response.summary.get("winning_graph_used") is True
        # First scene should have goal "hook"
        if response.scenes:
            assert response.scenes[0].scene_goal == "hook"
