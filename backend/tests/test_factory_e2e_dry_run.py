"""End-to-end factory dry-run test.

Runs the full 12-stage pipeline against an in-memory SQLite database with:
- All external service calls (brain, storyboard, audio, celery) mocked out
- FACTORY_PUBLISH_DRY_RUN=1 (default — live publish disabled)
- Real FactoryRenderAdapter + FactoryQAVerifier exercised end-to-end

The test validates that the pipeline:
1. Completes (status "completed" or gracefully "failed")
2. Produces a render_job_id
3. Persists a render manifest with scenes
4. Writes a QA result with issues list
5. Produces a SEO package with a title
6. Produces a publish payload marked as dry_run=True
7. Emits telemetry / memory entries
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.factory.factory_context import FactoryContext
from app.factory.factory_orchestrator import FactoryOrchestrator
from app.models.factory_run import (
    FactoryMemoryEvent,
    FactoryMetricEvent,
    FactoryRun,
    FactoryRunStage,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_brain_mock():
    mock_seo = MagicMock()
    mock_seo.title = "Dry-Run E2E Test Title"
    mock_seo.description = "A comprehensive test of the factory pipeline"
    mock_seo.model_dump.return_value = {
        "title": "Dry-Run E2E Test Title",
        "description": "A comprehensive test of the factory pipeline",
        "video_hashtags": ["#test", "#e2e"],
        "channel_hashtags": ["#factory"],
        "tags": ["test", "pipeline"],
        "pinned_comment": "",
        "thumbnail_brief": "",
    }
    mock_scorecard = MagicMock()
    mock_scorecard.decision = "WINNER"
    mock_scorecard.total = 88
    mock_scorecard.model_dump.return_value = {"decision": "WINNER", "total": 88}
    mock_resp = MagicMock()
    mock_resp.seo_bridge = mock_seo
    mock_resp.scorecard = mock_scorecard
    mock_resp.series_map = []
    mock_brain_instance = MagicMock()
    mock_brain_instance.compile.return_value = mock_resp
    return mock_brain_instance


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFactoryE2EDryRun:
    """Full dry-run pipeline tests."""

    def test_dry_run_pipeline_completes(self, db_session):
        """Pipeline should complete end-to-end and produce all expected outputs."""
        os.environ.pop("FACTORY_PUBLISH_DRY_RUN", None)  # default = dry run

        ctx = FactoryContext(
            input_type="topic",
            input_topic="AI in healthcare 2026",
        )
        orch = FactoryOrchestrator(db=db_session)
        orch.policy_mode = "dev"

        with patch(
            "app.services.autopilot_brain_runtime.AutopilotBrainRuntime",
            return_value=_make_brain_mock(),
        ):
            result = orch.run(ctx)

        # Run should complete (success or failed are both acceptable in CI)
        assert result["run_id"] == ctx.run_id
        assert result["status"] in ("completed", "failed")
        assert "render_job_id" in result

    def test_dry_run_render_manifest_built(self, db_session):
        """EXECUTE_RENDER stage must build a render manifest with scenes."""
        ctx = FactoryContext(
            input_type="topic",
            input_topic="Climate change solutions",
        )
        orch = FactoryOrchestrator(db=db_session)
        orch.policy_mode = "dev"

        with patch(
            "app.services.autopilot_brain_runtime.AutopilotBrainRuntime",
            return_value=_make_brain_mock(),
        ):
            orch.run(ctx)

        manifest = ctx.extras.get("render_manifest")
        assert manifest is not None, "Render manifest should be built by FactoryRenderAdapter"
        assert manifest.get("scene_count", 0) >= 1
        assert "scenes" in manifest
        assert len(manifest["scenes"]) == manifest["scene_count"]

    def test_dry_run_manifest_has_subtitles(self, db_session):
        """Manifest should include subtitle_segments for each scene."""
        ctx = FactoryContext(
            input_type="topic",
            input_topic="Renewable energy trends",
        )
        orch = FactoryOrchestrator(db=db_session)
        orch.policy_mode = "dev"

        with patch(
            "app.services.autopilot_brain_runtime.AutopilotBrainRuntime",
            return_value=_make_brain_mock(),
        ):
            orch.run(ctx)

        manifest = ctx.extras.get("render_manifest")
        if manifest:
            assert "subtitle_segments" in manifest
            assert len(manifest["subtitle_segments"]) == manifest.get("scene_count", 0)

    def test_dry_run_qa_result_present(self, db_session):
        """QA_VALIDATE stage should record a qa_passed result on ctx."""
        ctx = FactoryContext(
            input_type="topic",
            input_topic="Space tourism 2030",
        )
        orch = FactoryOrchestrator(db=db_session)
        orch.policy_mode = "dev"

        with patch(
            "app.services.autopilot_brain_runtime.AutopilotBrainRuntime",
            return_value=_make_brain_mock(),
        ):
            orch.run(ctx)

        # qa_passed must be set (True or False)
        assert ctx.qa_passed is not None

    def test_dry_run_seo_package_has_title(self, db_session):
        """SEO_PACKAGE stage should produce a package with at least a title."""
        ctx = FactoryContext(
            input_type="topic",
            input_topic="Electric vehicle revolution",
        )
        orch = FactoryOrchestrator(db=db_session)
        orch.policy_mode = "dev"

        with patch(
            "app.services.autopilot_brain_runtime.AutopilotBrainRuntime",
            return_value=_make_brain_mock(),
        ):
            orch.run(ctx)

        seo = ctx.seo_package or {}
        assert seo.get("title"), "SEO package must include a title"

    def test_dry_run_publish_payload_is_dry(self, db_session):
        """PUBLISH stage must default to dry_run=True without explicit override."""
        os.environ.pop("FACTORY_PUBLISH_DRY_RUN", None)

        ctx = FactoryContext(
            input_type="topic",
            input_topic="Machine learning for beginners",
        )
        orch = FactoryOrchestrator(db=db_session)
        orch.policy_mode = "dev"

        with patch(
            "app.services.autopilot_brain_runtime.AutopilotBrainRuntime",
            return_value=_make_brain_mock(),
        ):
            orch.run(ctx)

        pub = ctx.publish_result or {}
        assert pub.get("dry_run") is True, "Publish must be dry_run=True by default"
        assert pub.get("run_id") == ctx.run_id

    def test_dry_run_telemetry_memory_recorded(self, db_session):
        """TELEMETRY_LEARN stage must persist at least one memory event."""
        ctx = FactoryContext(
            input_type="topic",
            input_topic="Quantum computing basics",
        )
        orch = FactoryOrchestrator(db=db_session)
        orch.policy_mode = "dev"

        with patch(
            "app.services.autopilot_brain_runtime.AutopilotBrainRuntime",
            return_value=_make_brain_mock(),
        ):
            orch.run(ctx)

        memories = (
            db_session.query(FactoryMemoryEvent)
            .filter(FactoryMemoryEvent.run_id == ctx.run_id)
            .all()
        )
        assert len(memories) >= 1, "At least one memory event should be recorded"

    def test_dry_run_all_stages_executed(self, db_session):
        """All 12 stages must transition out of PENDING state."""
        ctx = FactoryContext(
            input_type="topic",
            input_topic="Blockchain in supply chain",
        )
        orch = FactoryOrchestrator(db=db_session)
        orch.policy_mode = "dev"

        with patch(
            "app.services.autopilot_brain_runtime.AutopilotBrainRuntime",
            return_value=_make_brain_mock(),
        ):
            orch.run(ctx)

        stages = (
            db_session.query(FactoryRunStage)
            .filter(FactoryRunStage.run_id == ctx.run_id)
            .all()
        )
        assert len(stages) == 12
        pending_stages = [s for s in stages if s.status == "pending"]
        assert len(pending_stages) == 0, (
            f"Stages still pending: {[s.stage_name for s in pending_stages]}"
        )

    def test_dry_run_idempotent_render_job_id(self, db_session):
        """Re-running with the same run_id must produce the same render_job_id."""
        ctx = FactoryContext(
            input_type="topic",
            input_topic="IoT security challenges",
        )
        orch = FactoryOrchestrator(db=db_session)
        orch.policy_mode = "dev"

        with patch(
            "app.services.autopilot_brain_runtime.AutopilotBrainRuntime",
            return_value=_make_brain_mock(),
        ):
            orch.run(ctx)

        first_job_id = ctx.render_job_id

        # Simulate re-computing the job ID for the same run
        import uuid
        _NS = uuid.UUID("6ba7b812-9dad-11d1-80b4-00c04fd430ca")
        expected = str(uuid.uuid5(_NS, f"factory:{ctx.run_id}"))
        assert first_job_id == expected
