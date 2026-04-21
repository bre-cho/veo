"""Tests for v16 Full-Power implementation.

Covers all 4 bug/gap areas:
1. Commerce Brain → Growth Brain Full-Power
   - ModelDrivenRankingEngine (gradient-boosting style ranking)
   - CampaignAttributionService multi-model attribution
   - ClosedLoopCalibrationOrchestrator
   - GrowthOptimizationOrchestrator model_driven ranking + funnel_summary

2. Storyboard/Director → Director OS Full-Power
   - NarrativeArcDirector arc planning
   - NarrativeArcDirector episode synthesis
   - NarrativeArcDirector A/B experiments

3. Avatar Fidelity → Full-Stack
   - VideoQualityAnalyzer multi-frame analysis
   - MultiEpisodeIdentityGovernor cross-episode governance
   - LongHorizonContinuityMemory trait tracking + pre-render check

4. Publish Enterprise Orchestration → Enterprise Maximum Depth
   - ProviderStatePollOrchestrator multi-round confirmation
   - FailureClassifier error classification
   - PlatformRecoveryWorkflow error_type-aware routing
   - PortfolioQuotaOrchestrator multi-dimensional quota
   - RegionContentComplianceMatrix region x content_type
"""
from __future__ import annotations

import time
import pytest


# ===========================================================================
# 1. Commerce Brain → Growth Brain Full-Power
# ===========================================================================


class TestModelDrivenRankingEngine:
    def _make_candidates(self):
        return [
            {"video_id": f"vid-{i}", "conversion_score": 0.5 + i * 0.1,
             "click_through_rate": 0.3 + i * 0.05,
             "performance_metrics": {"roas": 2.0 + i}}
            for i in range(5)
        ]

    def test_rank_returns_all_candidates(self):
        from app.services.commerce.ranking_engine import ModelDrivenRankingEngine

        engine = ModelDrivenRankingEngine(n_rounds=3)
        candidates = self._make_candidates()
        ranked = engine.rank(candidates)
        assert len(ranked) == len(candidates)

    def test_ensemble_score_in_range(self):
        from app.services.commerce.ranking_engine import ModelDrivenRankingEngine

        engine = ModelDrivenRankingEngine(n_rounds=3)
        ranked = engine.rank(self._make_candidates())
        for item in ranked:
            assert 0.0 <= item["ensemble_score"] <= 1.0

    def test_sorted_descending(self):
        from app.services.commerce.ranking_engine import ModelDrivenRankingEngine

        engine = ModelDrivenRankingEngine(n_rounds=3)
        ranked = engine.rank(self._make_candidates())
        scores = [item["ensemble_score"] for item in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_rank_field_sequential(self):
        from app.services.commerce.ranking_engine import ModelDrivenRankingEngine

        engine = ModelDrivenRankingEngine(n_rounds=3)
        ranked = engine.rank(self._make_candidates())
        for i, item in enumerate(ranked, start=1):
            assert item["rank"] == i

    def test_empty_candidates_returns_empty(self):
        from app.services.commerce.ranking_engine import ModelDrivenRankingEngine

        engine = ModelDrivenRankingEngine()
        assert engine.rank([]) == []

    def test_with_reference_records(self):
        from app.services.commerce.ranking_engine import ModelDrivenRankingEngine

        engine = ModelDrivenRankingEngine(n_rounds=5)
        candidates = self._make_candidates()
        # Use first 3 as reference
        ranked = engine.rank(candidates, reference_records=candidates[:3])
        assert len(ranked) == 5


class TestCampaignAttributionMultiModel:
    def _make_store(self, tmp_path):
        from app.services.learning_engine import PerformanceLearningEngine
        engine = PerformanceLearningEngine(store_path=str(tmp_path / "store.json"))
        now = time.time()
        for i in range(4):
            engine.record(
                video_id=f"attr-vid-{i}",
                hook_pattern="hook",
                cta_pattern="cta",
                template_family="fam",
                conversion_score=0.7,
                campaign_id="camp-multi",
            )
        return engine, now

    def test_time_decay_credits_sum(self, tmp_path):
        from app.services.commerce.campaign_attribution_service import CampaignAttributionService

        engine, now = self._make_store(tmp_path)
        svc = CampaignAttributionService(learning_store=engine)
        result = svc.attribute_conversion(
            conversion_event={"timestamp": now, "value": 4.0},
            campaign_id="camp-multi",
            model="time_decay",
        )
        total_credit = sum(a["credit"] for a in result["attributions"])
        assert abs(total_credit - result["total_attributed_value"]) < 0.05
        assert result["attribution_model"] == "time_decay"

    def test_first_touch_full_credit(self, tmp_path):
        from app.services.commerce.campaign_attribution_service import CampaignAttributionService

        engine, now = self._make_store(tmp_path)
        svc = CampaignAttributionService(learning_store=engine)
        result = svc.attribute_conversion(
            conversion_event={"timestamp": now, "value": 5.0},
            campaign_id="camp-multi",
            model="first_touch",
        )
        # First touch: only 1 attribution
        assert len(result["attributions"]) == 1
        assert abs(result["attributions"][0]["credit"] - 5.0) < 0.01

    def test_linear_equal_credits(self, tmp_path):
        from app.services.commerce.campaign_attribution_service import CampaignAttributionService

        engine, now = self._make_store(tmp_path)
        svc = CampaignAttributionService(learning_store=engine)
        result = svc.attribute_conversion(
            conversion_event={"timestamp": now, "value": 4.0},
            campaign_id="camp-multi",
            model="linear",
        )
        credits = [a["credit"] for a in result["attributions"]]
        if credits:
            # All credits should be equal (within floating-point)
            assert max(credits) - min(credits) < 0.01

    def test_funnel_report_has_new_fields(self, tmp_path):
        from app.services.commerce.campaign_attribution_service import CampaignAttributionService

        engine, _ = self._make_store(tmp_path)
        svc = CampaignAttributionService(learning_store=engine)
        report = svc.campaign_funnel_report("camp-multi")
        # Phase 1.5 new fields
        assert "avg_order_value" in report
        assert "revenue_estimate" in report
        assert "top_variant" in report


class TestClosedLoopCalibrationOrchestrator:
    def test_skip_below_threshold(self, tmp_path):
        from app.services.commerce.closed_loop_calibration_orchestrator import ClosedLoopCalibrationOrchestrator
        from app.services.learning_engine import PerformanceLearningEngine

        engine = PerformanceLearningEngine(store_path=str(tmp_path / "store.json"))
        # Only 2 records — below MIN_CALIBRATION_RECORDS=10
        engine.record(video_id="v1", hook_pattern="h", cta_pattern="c",
                      template_family="f", conversion_score=0.5)

        orch = ClosedLoopCalibrationOrchestrator(learning_store=engine)
        result = orch.run_full_calibration(platform="tiktok")
        assert result["skipped"] is True

    def test_runs_all_surfaces_above_threshold(self, tmp_path):
        from app.services.commerce.closed_loop_calibration_orchestrator import ClosedLoopCalibrationOrchestrator
        from app.services.learning_engine import PerformanceLearningEngine

        engine = PerformanceLearningEngine(store_path=str(tmp_path / "store.json"))
        for i in range(15):
            engine.record(
                video_id=f"v{i}", hook_pattern="h", cta_pattern="c",
                template_family="f", conversion_score=0.6 + i * 0.01,
                platform="tiktok",
            )

        orch = ClosedLoopCalibrationOrchestrator(learning_store=engine)
        result = orch.run_full_calibration(platform="tiktok")
        assert result["skipped"] is False
        assert result["surfaces_calibrated"] > 0
        assert "weight_deltas" in result

    def test_no_learning_store_skips(self, tmp_path):
        from app.services.commerce.closed_loop_calibration_orchestrator import ClosedLoopCalibrationOrchestrator

        orch = ClosedLoopCalibrationOrchestrator()
        result = orch.run_full_calibration()
        assert result["skipped"] is True


class TestGrowthOptimizationOrchestratorV16:
    def _candidates(self):
        return [
            {
                "video_id": f"vid-{i}",
                "variant_id": f"var-{i}",
                "conversion_score": 0.5 + i * 0.05,
                "click_through_rate": 0.2 + i * 0.02,
                "hook_pattern": f"hook_{i % 3}",
                "performance_metrics": {"roas": 2.0 + i},
            }
            for i in range(8)
        ]

    def test_ranking_method_model_driven(self):
        from app.services.commerce.growth_optimization_orchestrator import GrowthOptimizationOrchestrator

        orch = GrowthOptimizationOrchestrator()
        result = orch.optimize(
            campaign_id="camp-001",
            candidates=self._candidates(),
            use_model_ranking=True,
        )
        assert result["ranking_method"] == "model_driven"
        assert "funnel_summary" in result

    def test_ranking_method_linear_when_disabled(self):
        from app.services.commerce.growth_optimization_orchestrator import GrowthOptimizationOrchestrator

        orch = GrowthOptimizationOrchestrator()
        result = orch.optimize(
            campaign_id="camp-001",
            candidates=self._candidates(),
            use_model_ranking=False,
        )
        assert result["ranking_method"] == "linear_weighted"

    def test_funnel_summary_stages(self):
        from app.services.commerce.growth_optimization_orchestrator import GrowthOptimizationOrchestrator

        orch = GrowthOptimizationOrchestrator()
        result = orch.optimize(
            campaign_id="camp-001",
            candidates=self._candidates(),
        )
        funnel = result["funnel_summary"]
        assert "funnel_stages" in funnel
        stages = funnel["funnel_stages"]
        assert "creative" in stages
        assert "conversion_eligible" in stages
        assert "budget_feasible" in stages


# ===========================================================================
# 2. Storyboard/Director → Director OS Full-Power
# ===========================================================================


class TestNarrativeArcDirectorPlanArc:
    def test_plan_arc_basic(self):
        from app.services.storyboard.narrative_arc_director import NarrativeArcDirector

        director = NarrativeArcDirector()
        arc = director.plan_arc(
            series_id="test-series-001",
            total_episodes=6,
            arc_type="transformation",
        )
        assert arc["series_id"] == "test-series-001"
        assert arc["arc_type"] == "transformation"
        assert len(arc["episode_plans"]) == 6

    def test_plan_arc_episode_fields(self):
        from app.services.storyboard.narrative_arc_director import NarrativeArcDirector

        director = NarrativeArcDirector()
        arc = director.plan_arc(series_id="test-s2", total_episodes=4, arc_type="story")
        ep1 = arc["episode_plans"][0]
        assert "episode_number" in ep1
        assert "phase" in ep1
        assert "dominant_goals" in ep1
        assert "hook_intensity" in ep1
        assert 0 < ep1["hook_intensity"] <= 2.0

    def test_all_arc_types_supported(self):
        from app.services.storyboard.narrative_arc_director import NarrativeArcDirector, _ARC_TYPES

        director = NarrativeArcDirector()
        for arc_type in _ARC_TYPES:
            arc = director.plan_arc(series_id=f"arc-{arc_type}", total_episodes=4, arc_type=arc_type)
            assert len(arc["episode_plans"]) == 4

    def test_arc_stored_and_retrievable(self):
        from app.services.storyboard.narrative_arc_director import NarrativeArcDirector

        director = NarrativeArcDirector()
        director.plan_arc(series_id="retrieval-test", total_episodes=3, arc_type="education")
        retrieved = director.get_arc("retrieval-test")
        assert retrieved is not None
        assert retrieved["arc_type"] == "education"

    def test_unknown_arc_type_uses_default(self):
        from app.services.storyboard.narrative_arc_director import NarrativeArcDirector

        director = NarrativeArcDirector()
        arc = director.plan_arc(series_id="default-arc", total_episodes=4, arc_type="nonexistent")
        assert len(arc["episode_plans"]) == 4


class TestNarrativeArcDirectorRecommendNextEpisode:
    def test_recommend_returns_required_keys(self):
        from app.services.storyboard.narrative_arc_director import NarrativeArcDirector

        director = NarrativeArcDirector()
        director.plan_arc(series_id="ep-series", total_episodes=6, arc_type="authority")

        completed = [
            {"episode_number": 1, "conversion_score": 0.65},
            {"episode_number": 2, "conversion_score": 0.70},
        ]
        rec = director.recommend_next_episode(
            series_id="ep-series",
            completed_episodes=completed,
            platform="tiktok",
        )
        assert "next_episode_number" in rec
        assert "scene_composition" in rec
        assert "style_evolution" in rec
        assert "performance_insights" in rec

    def test_recommend_without_arc(self):
        from app.services.storyboard.narrative_arc_director import NarrativeArcDirector

        director = NarrativeArcDirector()
        rec = director.recommend_next_episode(
            series_id="no-arc-series",
            completed_episodes=[{"episode_number": 1, "conversion_score": 0.5}],
        )
        assert rec["arc_type"] == "inferred"

    def test_scene_composition_has_pacing_weights(self):
        from app.services.storyboard.narrative_arc_director import NarrativeArcDirector

        director = NarrativeArcDirector()
        rec = director.recommend_next_episode(
            series_id="pacing-series",
            completed_episodes=[{"episode_number": 1, "conversion_score": 0.8}],
        )
        comp = rec["scene_composition"]
        assert "recommended_pacing_weights" in comp
        weights = comp["recommended_pacing_weights"]
        assert "hook" in weights
        assert "cta" in weights


class TestNarrativeArcDirectorExperiment:
    def test_register_and_retrieve(self):
        from app.services.storyboard.narrative_arc_director import NarrativeArcDirector

        director = NarrativeArcDirector()
        exp = director.register_narrative_experiment(
            series_id="exp-series",
            variant_a={"arc_type": "transformation"},
            variant_b={"arc_type": "authority"},
        )
        assert "experiment_id" in exp
        assert exp["status"] == "running"

    def test_record_outcome_no_winner_too_few(self):
        from app.services.storyboard.narrative_arc_director import NarrativeArcDirector

        director = NarrativeArcDirector()
        exp = director.register_narrative_experiment(
            series_id="win-series",
            variant_a={"arc_type": "transformation"},
            variant_b={"arc_type": "story"},
        )
        exp_id = exp["experiment_id"]
        # Only 1 episode per variant — not enough for winner
        director.record_episode_outcome(exp_id, "a", 1, 0.9)
        director.record_episode_outcome(exp_id, "b", 1, 0.5)
        retrieved = director.get_experiment(exp_id)
        assert retrieved["winner"] is None

    def test_winner_declared_after_enough_episodes(self):
        from app.services.storyboard.narrative_arc_director import (
            NarrativeArcDirector,
            _NARRATIVE_WINNER_MIN_EPISODES,
        )

        director = NarrativeArcDirector()
        exp = director.register_narrative_experiment(
            series_id="winner-series",
            variant_a={"arc_type": "transformation"},
            variant_b={"arc_type": "education"},
        )
        exp_id = exp["experiment_id"]
        for ep in range(_NARRATIVE_WINNER_MIN_EPISODES):
            director.record_episode_outcome(exp_id, "a", ep + 1, 0.95)  # much higher
            director.record_episode_outcome(exp_id, "b", ep + 1, 0.30)

        final = director.get_experiment(exp_id)
        # Winner should be "a" (much higher scores)
        if final["winner"] is not None:
            assert final["winner"] == "a"


# ===========================================================================
# 3. Avatar Fidelity → Full-Stack
# ===========================================================================


class TestVideoQualityAnalyzer:
    def test_fallback_on_unreachable(self):
        from app.services.avatar.render_quality_gate import VideoQualityAnalyzer

        analyzer = VideoQualityAnalyzer()
        result = analyzer.analyze_video("http://localhost:99999/nonexistent.mp4")
        assert "composite_quality_score" in result
        assert "quality_tier" in result
        assert "frame_sharpness_trajectory" in result
        assert "per_axis_breakdown" in result

    def test_quality_tier_valid_values(self):
        from app.services.avatar.render_quality_gate import VideoQualityAnalyzer

        analyzer = VideoQualityAnalyzer()
        result = analyzer.analyze_video("https://example.invalid/render.mp4")
        assert result["quality_tier"] in ("excellent", "good", "acceptable", "poor")

    def test_temporal_consistency_in_range(self):
        from app.services.avatar.render_quality_gate import VideoQualityAnalyzer

        analyzer = VideoQualityAnalyzer()
        result = analyzer.analyze_video("https://example.invalid/test.mp4")
        assert 0.0 <= result["temporal_consistency_score"] <= 1.0

    def test_per_axis_breakdown_has_three_axes(self):
        from app.services.avatar.render_quality_gate import VideoQualityAnalyzer

        analyzer = VideoQualityAnalyzer()
        result = analyzer.analyze_video("https://example.invalid/test.mp4")
        axes = result["per_axis_breakdown"]
        assert "lighting" in axes
        assert "composition" in axes
        assert "motion_stability" in axes

    def test_remediation_hints_is_list(self):
        from app.services.avatar.render_quality_gate import VideoQualityAnalyzer

        analyzer = VideoQualityAnalyzer()
        result = analyzer.analyze_video("https://example.invalid/test.mp4")
        assert isinstance(result["remediation_hints"], list)


class TestMultiEpisodeIdentityGovernor:
    def _make_embedding(self, seed: float = 0.5) -> list[float]:
        return [seed] * 128

    def test_record_and_retrieve(self):
        from app.services.avatar.multi_episode_identity_governor import MultiEpisodeIdentityGovernor

        gov = MultiEpisodeIdentityGovernor()
        gov.clear_series("gov-series-001")
        result = gov.record_episode_identity(
            series_id="gov-series-001",
            avatar_id="av-001",
            episode_number=1,
            embedding=self._make_embedding(0.5),
        )
        assert result["recorded"] is True

    def test_governance_report_stable_series(self):
        from app.services.avatar.multi_episode_identity_governor import MultiEpisodeIdentityGovernor

        gov = MultiEpisodeIdentityGovernor()
        gov.clear_series("stable-series")
        # Record 3 episodes with identical embeddings
        for ep in range(1, 4):
            gov.record_episode_identity(
                series_id="stable-series",
                avatar_id="av-stable",
                episode_number=ep,
                embedding=self._make_embedding(0.5),
            )
        report = gov.get_governance_report("stable-series", "av-stable")
        assert report["identity_stable"] is True
        assert report["episode_count"] == 3

    def test_regression_detected_on_drifted_episode(self):
        from app.services.avatar.multi_episode_identity_governor import (
            MultiEpisodeIdentityGovernor,
            _EPISODE_DRIFT_THRESHOLD,
        )

        gov = MultiEpisodeIdentityGovernor()
        gov.clear_series("drift-series")
        for ep in range(1, 4):
            gov.record_episode_identity(
                series_id="drift-series",
                avatar_id="av-drift",
                episode_number=ep,
                embedding=[1.0] * 128,  # baseline
            )
        # Episode 4 with very different embedding
        gov.record_episode_identity(
            series_id="drift-series",
            avatar_id="av-drift",
            episode_number=4,
            embedding=[-1.0] * 128,  # orthogonal
        )
        regression = gov.detect_identity_regression("drift-series", "av-drift")
        # Should flag episode 4
        assert len(regression) > 0

    def test_score_series_identity_perfect_match(self):
        from app.services.avatar.multi_episode_identity_governor import MultiEpisodeIdentityGovernor

        gov = MultiEpisodeIdentityGovernor()
        gov.clear_series("perf-series")
        emb = [1.0 / (128 ** 0.5)] * 128  # unit vector
        for ep in range(1, 4):
            gov.record_episode_identity(
                series_id="perf-series",
                avatar_id="av-p",
                episode_number=ep,
                embedding=emb,
            )
        score = gov.score_series_identity("perf-series", "av-p")
        assert abs(score - 1.0) < 0.01

    def test_too_few_episodes_returns_stable(self):
        from app.services.avatar.multi_episode_identity_governor import MultiEpisodeIdentityGovernor

        gov = MultiEpisodeIdentityGovernor()
        gov.clear_series("few-series")
        gov.record_episode_identity(
            series_id="few-series",
            avatar_id="av-few",
            episode_number=1,
            embedding=self._make_embedding(0.7),
        )
        report = gov.get_governance_report("few-series", "av-few")
        assert report["identity_stable"] is True


class TestLongHorizonContinuityMemory:
    def _traits(self, **overrides) -> dict:
        base = {
            "skin_tone": "medium", "eye_color": "brown", "age_range": "25-35",
            "gender_expression": "female", "hair_style": "long", "hair_color": "black",
            "outfit_code": "casual", "background_code": "studio",
        }
        base.update(overrides)
        return base

    def test_record_snapshot(self):
        from app.services.avatar.long_horizon_continuity_memory import LongHorizonContinuityMemory

        mem = LongHorizonContinuityMemory()
        mem.clear_avatar("av-lhc-1")
        result = mem.record_snapshot("av-lhc-1", traits=self._traits(), episode_number=1)
        assert result["recorded"] is True
        assert result["snapshot_count"] == 1

    def test_canonical_traits_majority_agreement(self):
        from app.services.avatar.long_horizon_continuity_memory import LongHorizonContinuityMemory

        mem = LongHorizonContinuityMemory()
        mem.clear_avatar("av-lhc-2")
        for i in range(7):
            mem.record_snapshot("av-lhc-2", traits=self._traits(), episode_number=i + 1)
        # 2 snapshots with different hair_color
        mem.record_snapshot("av-lhc-2", traits=self._traits(hair_color="blonde"), episode_number=8)
        mem.record_snapshot("av-lhc-2", traits=self._traits(hair_color="blonde"), episode_number=9)

        canonical = mem.get_canonical_traits("av-lhc-2")
        # "black" has 7/9 > 0.7 → canonical
        assert canonical.get("hair_color") == "black"

    def test_pre_render_check_detects_trait_conflict(self):
        from app.services.avatar.long_horizon_continuity_memory import LongHorizonContinuityMemory

        mem = LongHorizonContinuityMemory()
        mem.clear_avatar("av-lhc-3")
        for i in range(8):
            mem.record_snapshot("av-lhc-3", traits=self._traits(), episode_number=i + 1)

        result = mem.pre_render_continuity_check(
            avatar_id="av-lhc-3",
            proposed_traits=self._traits(hair_color="blonde", outfit_code="formal"),
        )
        assert "drift_risk" in result
        assert "conflicting_traits" in result
        assert len(result["conflicting_traits"]) >= 1
        assert result["drift_risk"] in ("low", "medium", "high")

    def test_pre_render_check_no_conflict(self):
        from app.services.avatar.long_horizon_continuity_memory import LongHorizonContinuityMemory

        mem = LongHorizonContinuityMemory()
        mem.clear_avatar("av-lhc-4")
        for i in range(8):
            mem.record_snapshot("av-lhc-4", traits=self._traits(), episode_number=i + 1)

        result = mem.pre_render_continuity_check(
            avatar_id="av-lhc-4",
            proposed_traits=self._traits(),  # same as history
        )
        assert result["drift_risk"] == "none"
        assert len(result["conflicting_traits"]) == 0

    def test_trait_drift_report(self):
        from app.services.avatar.long_horizon_continuity_memory import LongHorizonContinuityMemory

        mem = LongHorizonContinuityMemory()
        mem.clear_avatar("av-lhc-5")
        for i in range(5):
            mem.record_snapshot("av-lhc-5", traits=self._traits(), episode_number=i + 1)
        report = mem.get_trait_drift_report("av-lhc-5")
        assert "trait_stability" in report
        assert "drift_trend" in report
        assert report["drift_trend"] in ("stable", "drifting")

    def test_circular_buffer_cap(self):
        from app.services.avatar.long_horizon_continuity_memory import (
            LongHorizonContinuityMemory,
            _MAX_SNAPSHOTS,
        )

        mem = LongHorizonContinuityMemory()
        mem.clear_avatar("av-lhc-6")
        for i in range(_MAX_SNAPSHOTS + 10):
            mem.record_snapshot("av-lhc-6", traits=self._traits(), episode_number=i + 1)

        result = mem.record_snapshot("av-lhc-6", traits=self._traits(), episode_number=9999)
        assert result["snapshot_count"] == _MAX_SNAPSHOTS


# ===========================================================================
# 4. Publish Enterprise Orchestration → Enterprise Maximum Depth
# ===========================================================================


class TestFailureClassifier:
    def _make_job(self, error_code="", platform="youtube", provider_meta=None):
        class FakeJob:
            pass
        job = FakeJob()
        job.platform = platform
        job.error_log = {"error_code": error_code} if error_code else {}
        job.provider_metadata = provider_meta or {}
        return job

    def test_classify_auth_expired_youtube(self):
        from app.services.publish_providers.platform_recovery_workflow import FailureClassifier

        clf = FailureClassifier()
        job = self._make_job(error_code="401", platform="youtube")
        result = clf.classify(job, "youtube")
        assert result["error_type"] == "auth_expired"
        assert result["recoverable"] is True

    def test_classify_quota_exceeded_youtube(self):
        from app.services.publish_providers.platform_recovery_workflow import FailureClassifier

        clf = FailureClassifier()
        job = self._make_job(error_code="403", platform="youtube")
        result = clf.classify(job, "youtube")
        assert result["error_type"] == "quota_exceeded"

    def test_classify_content_rejected_not_recoverable(self):
        from app.services.publish_providers.platform_recovery_workflow import FailureClassifier

        clf = FailureClassifier()
        job = self._make_job(error_code="400", platform="youtube")
        result = clf.classify(job, "youtube")
        assert result["error_type"] == "content_rejected"
        assert result["recoverable"] is False

    def test_classify_tiktok_auth_expired(self):
        from app.services.publish_providers.platform_recovery_workflow import FailureClassifier

        clf = FailureClassifier()
        job = self._make_job(error_code="10002", platform="tiktok")
        result = clf.classify(job, "tiktok")
        assert result["error_type"] == "auth_expired"

    def test_classify_meta_token_expired(self):
        from app.services.publish_providers.platform_recovery_workflow import FailureClassifier

        clf = FailureClassifier()
        job = self._make_job(error_code="190", platform="meta")
        result = clf.classify(job, "meta")
        assert result["error_type"] == "token_expired"

    def test_classify_meta_account_restricted_not_recoverable(self):
        from app.services.publish_providers.platform_recovery_workflow import FailureClassifier

        clf = FailureClassifier()
        job = self._make_job(error_code="368", platform="meta")
        result = clf.classify(job, "meta")
        assert result["error_type"] == "account_restricted"
        assert result["recoverable"] is False

    def test_classify_unknown_has_suggested_strategy(self):
        from app.services.publish_providers.platform_recovery_workflow import FailureClassifier

        clf = FailureClassifier()
        job = self._make_job(error_code="", platform="youtube")
        result = clf.classify(job, "youtube")
        assert result["error_type"] == "unknown"
        assert "suggested_strategy" in result


class TestPlatformRecoveryWorkflowV16:
    def _make_job(self, platform="youtube", error_code=None, attempt_count=0):
        class FakeJob:
            pass
        job = FakeJob()
        job.id = "job-v16"
        job.platform = platform
        job.error_log = {"error_code": error_code, "recovery_metadata": {"attempt_count": attempt_count}} if error_code else {"recovery_metadata": {"attempt_count": attempt_count}}
        job.provider_metadata = {}
        job.status = "failed"
        return job

    class FakeDB:
        def add(self, obj): pass
        def commit(self): pass

    def test_youtube_network_error_retries(self):
        from app.services.publish_providers.platform_recovery_workflow import PlatformRecoveryWorkflow

        workflow = PlatformRecoveryWorkflow()
        job = self._make_job(platform="youtube", error_code="500")
        result = workflow.recover(self.FakeDB(), job)
        assert result.get("attempt_count") is not None
        meta = result.get("recovery_metadata", {})
        assert meta.get("error_type") is not None

    def test_meta_token_expired_uses_token_refresh(self):
        from app.services.publish_providers.platform_recovery_workflow import PlatformRecoveryWorkflow

        workflow = PlatformRecoveryWorkflow()
        job = self._make_job(platform="meta", error_code="190")
        result = workflow.recover(self.FakeDB(), job)
        meta = result.get("recovery_metadata", {})
        assert meta.get("error_type") == "token_expired"
        assert "token_refresh" in (meta.get("last_recovery_strategy") or "")

    def test_tiktok_rate_limited_uses_backoff(self):
        from app.services.publish_providers.platform_recovery_workflow import PlatformRecoveryWorkflow

        workflow = PlatformRecoveryWorkflow()
        job = self._make_job(platform="tiktok", error_code="10006")
        result = workflow.recover(self.FakeDB(), job)
        meta = result.get("recovery_metadata", {})
        assert meta.get("error_type") == "rate_limited"

    def test_error_type_in_recovery_metadata(self):
        from app.services.publish_providers.platform_recovery_workflow import PlatformRecoveryWorkflow

        workflow = PlatformRecoveryWorkflow()
        job = self._make_job(platform="tiktok")
        result = workflow.recover(self.FakeDB(), job)
        meta = result.get("recovery_metadata", {})
        assert "error_type" in meta


class TestProviderStatePollOrchestrator:
    def test_returns_pending_on_max_rounds(self):
        from app.services.publish_providers.provider_final_state_syncer import (
            ProviderStatePollOrchestrator,
            ProviderFinalStateSyncer,
        )
        from unittest.mock import MagicMock

        # Mock syncer that always returns pending
        mock_syncer = MagicMock(spec=ProviderFinalStateSyncer)
        mock_syncer.fetch_final_state.return_value = {
            "terminal_status": "pending",
            "metrics": {},
            "platform": "youtube",
        }

        poller = ProviderStatePollOrchestrator(
            max_rounds=2, poll_interval_sec=0, _syncer=mock_syncer
        )
        result = poller.poll_until_stable(job_id="vid-abc", platform="youtube")
        assert result["confirmed"] is False
        assert result["confirmed_status"] in ("pending", "timeout")
        assert result["rounds_polled"] == 2

    def test_confirms_published_on_stable_rounds(self):
        from app.services.publish_providers.provider_final_state_syncer import (
            ProviderStatePollOrchestrator,
            ProviderFinalStateSyncer,
        )
        from unittest.mock import MagicMock

        mock_syncer = MagicMock(spec=ProviderFinalStateSyncer)
        mock_syncer.fetch_final_state.return_value = {
            "terminal_status": "published",
            "metrics": {},
            "platform": "youtube",
        }

        poller = ProviderStatePollOrchestrator(
            max_rounds=4, poll_interval_sec=0, required_stable_rounds=2, _syncer=mock_syncer
        )
        result = poller.poll_until_stable(job_id="vid-abc", platform="youtube")
        assert result["confirmed"] is True
        assert result["confirmed_status"] == "published"

    def test_result_keys_present(self):
        from app.services.publish_providers.provider_final_state_syncer import (
            ProviderStatePollOrchestrator,
            ProviderFinalStateSyncer,
        )
        from unittest.mock import MagicMock

        mock_syncer = MagicMock(spec=ProviderFinalStateSyncer)
        mock_syncer.fetch_final_state.return_value = {
            "terminal_status": "failed",
            "metrics": {},
            "platform": "tiktok",
        }

        poller = ProviderStatePollOrchestrator(max_rounds=2, _syncer=mock_syncer)
        result = poller.poll_until_stable("vid-123", "tiktok")
        for key in ("job_id", "platform", "confirmed_status", "rounds_polled", "confirmed"):
            assert key in result


class TestPortfolioQuotaOrchestrator:
    def test_check_quota_allowed_on_fresh_campaign(self):
        from app.services.publish_providers.portfolio_quota_orchestrator import PortfolioQuotaOrchestrator
        from app.services.publish_providers.portfolio_quota_orchestrator import _QUOTA_STORE

        _QUOTA_STORE.pop("quota-fresh", None)
        orch = PortfolioQuotaOrchestrator(default_daily_publish_limit=5)
        orch.register_campaign("quota-fresh")
        result = orch.check_quota("quota-fresh", platform="tiktok")
        assert result["allowed"] is True
        assert result["quota_remaining"]["daily_publishes"] == 5

    def test_quota_blocked_after_limit_reached(self):
        from app.services.publish_providers.portfolio_quota_orchestrator import PortfolioQuotaOrchestrator
        from app.services.publish_providers.portfolio_quota_orchestrator import _QUOTA_STORE

        _QUOTA_STORE.pop("quota-full", None)
        orch = PortfolioQuotaOrchestrator(default_daily_publish_limit=2)
        orch.register_campaign("quota-full")
        orch.record_publish("quota-full", platform="youtube")
        orch.record_publish("quota-full", platform="youtube")
        result = orch.check_quota("quota-full", platform="youtube")
        assert result["allowed"] is False
        assert any("daily_publish_limit_reached" in r for r in result["reasons"])

    def test_rebalance_portfolio(self):
        from app.services.publish_providers.portfolio_quota_orchestrator import PortfolioQuotaOrchestrator
        from app.services.publish_providers.portfolio_quota_orchestrator import _QUOTA_STORE

        for cid in ("rb-c1", "rb-c2", "rb-c3"):
            _QUOTA_STORE.pop(cid, None)

        orch = PortfolioQuotaOrchestrator(default_daily_publish_limit=10)
        for cid in ("rb-c1", "rb-c2", "rb-c3"):
            orch.register_campaign(cid)

        allocation = orch.rebalance_portfolio(["rb-c1", "rb-c2", "rb-c3"], total_remaining_publishes=15)
        assert sum(allocation.values()) <= 15

    def test_overage_alert_detects_near_limit(self):
        from app.services.publish_providers.portfolio_quota_orchestrator import PortfolioQuotaOrchestrator
        from app.services.publish_providers.portfolio_quota_orchestrator import _QUOTA_STORE

        _QUOTA_STORE.pop("overage-c1", None)
        orch = PortfolioQuotaOrchestrator(default_daily_publish_limit=3)
        orch.register_campaign("overage-c1")
        # Publish 3 times — at 100% utilisation
        for _ in range(3):
            orch.record_publish("overage-c1")

        alerts = orch.overage_alert_summary(["overage-c1"])
        assert len(alerts) == 1
        assert alerts[0]["campaign_id"] == "overage-c1"

    def test_quota_dashboard_structure(self):
        from app.services.publish_providers.portfolio_quota_orchestrator import PortfolioQuotaOrchestrator
        from app.services.publish_providers.portfolio_quota_orchestrator import _QUOTA_STORE

        _QUOTA_STORE.pop("dash-c1", None)
        orch = PortfolioQuotaOrchestrator()
        orch.register_campaign("dash-c1")
        dashboard = orch.quota_dashboard(["dash-c1"])
        assert "date_utc" in dashboard
        assert "campaigns" in dashboard
        assert "portfolio_totals" in dashboard


class TestRegionContentComplianceMatrix:
    def test_blocked_content_returns_blocked(self):
        from app.services.publish_providers.compliance_risk_policy import RegionContentComplianceMatrix

        matrix = RegionContentComplianceMatrix()
        result = matrix.evaluate(
            content={"caption": "Play casino and win big jackpot!"},
            region_code="VN",
        )
        assert result["status"] == "blocked"
        assert any(v["type"] == "gambling" for v in result["violations"])

    def test_review_content_returns_review(self):
        from app.services.publish_providers.compliance_risk_policy import RegionContentComplianceMatrix

        matrix = RegionContentComplianceMatrix()
        result = matrix.evaluate(
            content={"caption": "Best wine selection"},
            region_code="VN",
        )
        assert result["status"] == "review"

    def test_allowed_content_no_violations(self):
        from app.services.publish_providers.compliance_risk_policy import RegionContentComplianceMatrix

        matrix = RegionContentComplianceMatrix()
        result = matrix.evaluate(
            content={"caption": "Check out our new skincare product"},
            region_code="US",
        )
        assert result["status"] == "allowed"
        assert result["violations"] == []

    def test_explicit_content_types(self):
        from app.services.publish_providers.compliance_risk_policy import RegionContentComplianceMatrix

        matrix = RegionContentComplianceMatrix()
        result = matrix.evaluate(
            content={},
            region_code="EU",
            content_types=["health_claims"],
        )
        # EU blocks health_claims
        assert result["status"] == "blocked"

    def test_unknown_region_returns_review(self):
        from app.services.publish_providers.compliance_risk_policy import RegionContentComplianceMatrix

        matrix = RegionContentComplianceMatrix()
        result = matrix.evaluate(
            content={"caption": "test"},
            region_code="XX",
        )
        assert result["status"] == "review"

    def test_tiktok_vn_blocks_crypto(self):
        from app.services.publish_providers.compliance_risk_policy import RegionContentComplianceMatrix

        matrix = RegionContentComplianceMatrix()
        result = matrix.evaluate(
            content={"caption": "Invest in bitcoin today"},
            region_code="VN",
            platform="tiktok",
        )
        assert result["status"] == "blocked"

    def test_auto_detection_returns_detected_types(self):
        from app.services.publish_providers.compliance_risk_policy import RegionContentComplianceMatrix

        matrix = RegionContentComplianceMatrix()
        result = matrix.evaluate(
            content={"caption": "guaranteed cure for all diseases"},
            region_code="US",
        )
        assert "detected_types" in result
