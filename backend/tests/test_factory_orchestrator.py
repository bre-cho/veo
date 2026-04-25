"""Tests for FactoryOrchestrator — each stage is exercised in isolation
using a real in-memory SQLite database (from conftest.py) and lightweight
mocks where necessary.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.factory.factory_context import FactoryContext
from app.factory.factory_orchestrator import FactoryOrchestrator
from app.factory.factory_state import FactoryStage
from app.models.factory_run import (
    FactoryRun,
    FactoryRunStage,
    FactoryQualityGate,
    FactoryMemoryEvent,
    FactoryMetricEvent,
    FactoryIncident,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ctx(**kwargs) -> FactoryContext:
    defaults = dict(input_type="topic", input_topic="AI trends 2026")
    defaults.update(kwargs)
    return FactoryContext(**defaults)


def _make_orchestrator(db_session) -> FactoryOrchestrator:
    orch = FactoryOrchestrator(db=db_session)
    orch.policy_mode = "dev"
    return orch


# ---------------------------------------------------------------------------
# start_run
# ---------------------------------------------------------------------------

class TestStartRun:
    def test_creates_run_and_stages(self, db_session):
        ctx = _make_ctx()
        orch = _make_orchestrator(db_session)
        run = orch.start_run(ctx)

        assert db_session.query(FactoryRun).filter(FactoryRun.id == ctx.run_id).first() is not None
        stage_rows = db_session.query(FactoryRunStage).filter(FactoryRunStage.run_id == ctx.run_id).all()
        assert len(stage_rows) == 12

    def test_run_initial_status_pending(self, db_session):
        ctx = _make_ctx()
        orch = _make_orchestrator(db_session)
        run = orch.start_run(ctx)
        assert run.status == "pending"


# ---------------------------------------------------------------------------
# _stage_intake
# ---------------------------------------------------------------------------

class TestStageIntake:
    def test_accepted(self, db_session):
        ctx = _make_ctx(input_topic="hello world")
        orch = _make_orchestrator(db_session)
        result = orch._stage_intake(ctx)
        assert result["accepted"] is True
        assert result["input_length"] == len("hello world")

    def test_empty_input(self, db_session):
        ctx = _make_ctx(input_topic=None, input_script=None)
        orch = _make_orchestrator(db_session)
        result = orch._stage_intake(ctx)
        assert result["accepted"] is True
        assert result["input_length"] == 0


# ---------------------------------------------------------------------------
# _stage_script_plan
# ---------------------------------------------------------------------------

class TestStageScriptPlan:
    def test_fallback_on_brain_failure(self, db_session):
        """When AutopilotBrainRuntime import fails, use fallback plan."""
        ctx = _make_ctx(input_topic="Test topic")
        orch = _make_orchestrator(db_session)
        ctx.selected_skill = "viral"

        with patch("builtins.__import__", side_effect=ImportError("no brain")):
            result = orch._stage_script_plan(ctx)

        assert "title" in result
        assert result["skill"] == "viral"
        assert result["scene_count"] >= 1

    def test_brain_runtime_called(self, db_session):
        """Script plan calls AutopilotBrainRuntime and returns structured output."""
        ctx = _make_ctx(input_topic="AI in 2026")
        orch = _make_orchestrator(db_session)

        # Mock brain response
        mock_seo = MagicMock()
        mock_seo.title = "AI in 2026: The Future"
        mock_seo.description = "Hook text"
        mock_seo.model_dump.return_value = {
            "title": "AI in 2026: The Future",
            "description": "Hook text",
            "video_hashtags": [],
            "channel_hashtags": [],
            "tags": [],
            "pinned_comment": "",
            "thumbnail_brief": "",
        }
        mock_scorecard = MagicMock()
        mock_scorecard.decision = "WINNER"
        mock_scorecard.total = 92
        mock_scorecard.model_dump.return_value = {"decision": "WINNER", "total": 92}
        mock_resp = MagicMock()
        mock_resp.seo_bridge = mock_seo
        mock_resp.scorecard = mock_scorecard
        mock_resp.series_map = []

        mock_brain = MagicMock()
        mock_brain.compile.return_value = mock_resp

        with patch("app.services.autopilot_brain_runtime.AutopilotBrainRuntime", return_value=mock_brain):
            result = orch._stage_script_plan(ctx)

        assert result["title"] == "AI in 2026: The Future"
        assert result["decision"] == "WINNER"
        assert ctx.script_plan is not None


# ---------------------------------------------------------------------------
# _stage_scene_build
# ---------------------------------------------------------------------------

class TestStageSceneBuild:
    def test_storyboard_fallback(self, db_session):
        """Falls back to simple scenes when storyboard import fails."""
        ctx = _make_ctx(input_topic="Nature beauty")
        ctx.script_plan = {"title": "Nature", "scene_count": 4}
        orch = _make_orchestrator(db_session)

        with patch("app.services.storyboard_engine.StoryboardEngine", side_effect=ImportError):
            result = orch._stage_scene_build(ctx)

        assert result["scene_count"] == 4
        assert len(ctx.scenes) == 4
        assert ctx.scenes[0]["scene_index"] == 0

    def test_scene_fields_present(self, db_session):
        """Each scene must include all required fields."""
        ctx = _make_ctx(input_script="Scene one. Scene two. Scene three.")
        ctx.script_plan = {"title": "Test", "scene_count": 3}
        orch = _make_orchestrator(db_session)

        with patch("app.services.storyboard_engine.StoryboardEngine", side_effect=ImportError):
            orch._stage_scene_build(ctx)

        required = {
            "scene_index", "voiceover", "visual_prompt", "avatar_instruction",
            "camera_instruction", "duration", "subtitle_text", "dependency_reason",
        }
        for scene in ctx.scenes:
            assert required.issubset(scene.keys()), f"Missing keys in scene: {scene.keys()}"


# ---------------------------------------------------------------------------
# _stage_avatar_audio_build
# ---------------------------------------------------------------------------

class TestStageAvatarAudio:
    def test_default_avatar_assigned(self, db_session):
        ctx = _make_ctx()
        orch = _make_orchestrator(db_session)
        result = orch._stage_avatar_audio_build(ctx)
        assert result["avatar_id"] == "default_avatar"

    def test_custom_avatar_id_respected(self, db_session):
        ctx = _make_ctx(input_avatar_id="avatar_123")
        orch = _make_orchestrator(db_session)
        result = orch._stage_avatar_audio_build(ctx)
        assert result["avatar_id"] == "avatar_123"

    def test_audio_service_failure_is_graceful(self, db_session):
        """Audio service failure should not block the stage."""
        ctx = _make_ctx(input_topic="test topic")
        orch = _make_orchestrator(db_session)

        with patch("app.services.audio.audio_mix_service.create_audio_render_output",
                   side_effect=RuntimeError("no audio")):
            result = orch._stage_avatar_audio_build(ctx)

        assert result["audio_url"] is None


# ---------------------------------------------------------------------------
# _stage_render_plan
# ---------------------------------------------------------------------------

class TestStageRenderPlan:
    def test_basic_plan_generated(self, db_session):
        ctx = _make_ctx()
        ctx.avatar_id = "av1"
        ctx.scenes = [{"scene_index": i} for i in range(5)]
        orch = _make_orchestrator(db_session)
        result = orch._stage_render_plan(ctx)

        assert result["scene_count"] == 5
        assert result["provider"] == "auto"
        assert "estimated_cost" in result
        assert "selected_strategy" in result

    def test_no_project_skips_decision_engine(self, db_session):
        ctx = _make_ctx()
        ctx.project_id = None
        ctx.scenes = [{"scene_index": 0}]
        ctx.avatar_id = "av1"
        orch = _make_orchestrator(db_session)
        result = orch._stage_render_plan(ctx)
        assert result["selected_strategy"] == "full_rebuild"


# ---------------------------------------------------------------------------
# _stage_execute_render
# ---------------------------------------------------------------------------

class TestStageExecuteRender:
    def test_render_job_id_generated(self, db_session):
        ctx = _make_ctx()
        orch = _make_orchestrator(db_session)
        result = orch._stage_execute_render(ctx)
        assert result["render_job_id"]
        assert ctx.render_job_id == result["render_job_id"]

    def test_no_project_id_does_not_dispatch(self, db_session):
        ctx = _make_ctx()
        ctx.project_id = None
        orch = _make_orchestrator(db_session)
        result = orch._stage_execute_render(ctx)
        assert result["dispatched"] is False

    def test_deterministic_job_id(self, db_session):
        """Same run_id should always produce the same render_job_id."""
        ctx = _make_ctx()
        orch = _make_orchestrator(db_session)
        r1 = orch._stage_execute_render(ctx)
        # Re-run — job_id must be identical
        r2 = orch._stage_execute_render(ctx)
        assert r1["render_job_id"] == r2["render_job_id"]


# ---------------------------------------------------------------------------
# _stage_qa_validate
# ---------------------------------------------------------------------------

class TestStageQAValidate:
    def test_passes_with_full_context(self, db_session):
        ctx = _make_ctx()
        ctx.scenes = [
            {
                "scene_index": i,
                "voiceover": f"Scene {i}",
                "subtitle_text": f"Subtitle {i}",
                "duration": 5.0,
            }
            for i in range(3)
        ]
        ctx.render_job_id = "rj-123"
        ctx.script_plan = {"title": "Test title", "decision": "WINNER"}
        ctx.avatar_id = "av1"
        ctx.render_plan = {"scene_count": 3}
        ctx.seo_package = {"title": "Test title", "description": "desc"}
        orch = _make_orchestrator(db_session)
        result = orch._stage_qa_validate(ctx)
        assert result["qa_passed"] is True
        assert result["issues"] == []

    def test_fails_with_no_scenes(self, db_session):
        ctx = _make_ctx()
        ctx.scenes = []
        ctx.render_job_id = "rj-123"
        ctx.script_plan = {"title": "T", "decision": "WINNER"}
        ctx.avatar_id = "av1"
        ctx.render_plan = {"scene_count": 0}
        orch = _make_orchestrator(db_session)
        result = orch._stage_qa_validate(ctx)
        assert result["qa_passed"] is False
        assert "no_scenes_built" in result["issues"]

    def test_fails_with_brain_block_decision(self, db_session):
        ctx = _make_ctx()
        ctx.scenes = [{"scene_index": 0}]
        ctx.render_job_id = "rj-456"
        ctx.script_plan = {"title": "Blocked", "decision": "BLOCK"}
        ctx.avatar_id = "av1"
        ctx.render_plan = {"scene_count": 1}
        orch = _make_orchestrator(db_session)
        result = orch._stage_qa_validate(ctx)
        assert result["qa_passed"] is False
        assert "brain_decision_block" in result["issues"]


# ---------------------------------------------------------------------------
# _stage_seo_package
# ---------------------------------------------------------------------------

class TestStageSEOPackage:
    def test_fallback_on_import_error(self, db_session):
        ctx = _make_ctx()
        ctx.script_plan = {"title": "Test title"}
        ctx.render_job_id = "rj-1"
        orch = _make_orchestrator(db_session)

        with patch("app.services.post_render_seo_orchestrator.PostRenderSEOOrchestrator",
                   side_effect=ImportError):
            result = orch._stage_seo_package(ctx)

        assert result.get("title") == "Test title"

    def test_seo_title_set_on_ctx(self, db_session):
        ctx = _make_ctx()
        ctx.script_plan = {"title": "AI Video"}
        ctx.render_job_id = "rj-99"
        ctx.scenes = []
        ctx.output_video_url = None
        orch = _make_orchestrator(db_session)
        result = orch._stage_seo_package(ctx)
        # Title should be in the SEO package
        assert "title" in result


# ---------------------------------------------------------------------------
# _stage_publish
# ---------------------------------------------------------------------------

class TestStagePublish:
    def test_dry_run_default(self, db_session):
        import os
        os.environ.pop("FACTORY_PUBLISH_DRY_RUN", None)
        ctx = _make_ctx()
        ctx.render_job_id = "rj-abc"
        ctx.seo_package = {"title": "Published", "description": "desc", "hashtags_video": []}
        ctx.script_plan = {"title": "Published"}
        ctx.output_video_url = None
        orch = _make_orchestrator(db_session)
        result = orch._stage_publish(ctx)
        assert result["dry_run"] is True
        assert result["status"] == "dry_run"

    def test_live_mode_when_env_set(self, db_session):
        import os
        os.environ["FACTORY_PUBLISH_DRY_RUN"] = "0"
        try:
            ctx = _make_ctx()
            ctx.render_job_id = "rj-live"
            ctx.seo_package = {"title": "Live", "description": "d", "hashtags_video": []}
            ctx.script_plan = {"title": "Live"}
            ctx.output_video_url = None
            orch = _make_orchestrator(db_session)
            result = orch._stage_publish(ctx)
            assert result["dry_run"] is False
            assert result["status"] == "scheduled"
        finally:
            os.environ.pop("FACTORY_PUBLISH_DRY_RUN", None)


# ---------------------------------------------------------------------------
# Full pipeline smoke test
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_run_completes(self, db_session):
        """Full pipeline run should complete without unhandled exceptions."""
        ctx = _make_ctx(input_topic="Space exploration 2026")
        orch = _make_orchestrator(db_session)

        # Mock brain to avoid network calls
        mock_seo = MagicMock()
        mock_seo.title = "Space exploration 2026"
        mock_seo.description = "The future of space"
        mock_seo.model_dump.return_value = {
            "title": "Space exploration 2026",
            "description": "The future of space",
            "video_hashtags": ["#space"],
            "channel_hashtags": [],
            "tags": [],
            "pinned_comment": "",
            "thumbnail_brief": "",
        }
        mock_scorecard = MagicMock()
        mock_scorecard.decision = "WINNER"
        mock_scorecard.total = 91
        mock_scorecard.model_dump.return_value = {"decision": "WINNER", "total": 91}
        mock_resp = MagicMock()
        mock_resp.seo_bridge = mock_seo
        mock_resp.scorecard = mock_scorecard
        mock_resp.series_map = []
        mock_brain_instance = MagicMock()
        mock_brain_instance.compile.return_value = mock_resp

        with patch("app.services.autopilot_brain_runtime.AutopilotBrainRuntime",
                   return_value=mock_brain_instance):
            result = orch.run(ctx)

        assert "run_id" in result
        assert result["run_id"] == ctx.run_id
        # Pipeline should complete (success or failed due to QA — either is acceptable in tests)
        assert result["status"] in ("completed", "failed")
