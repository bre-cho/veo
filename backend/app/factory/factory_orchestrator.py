"""factory_orchestrator – closed-loop Factory Orchestrator.

The FactoryOrchestrator is the single entry point for all video production
jobs.  It drives the 12-stage pipeline, persists every trace event via ORM
models, enforces quality gates, and stores learning memory after each run.

Typical usage (from the Celery worker)::

    from app.factory.factory_orchestrator import FactoryOrchestrator
    from app.factory.factory_context import FactoryContext

    ctx = FactoryContext(input_type="topic", input_topic="AI trends 2026")
    orchestrator = FactoryOrchestrator(db)
    result = orchestrator.run(ctx)

Each stage is implemented as a private ``_stage_*`` method.  Stages call into
existing services via thin adapter calls so that no service knows it is inside
a factory pipeline — the factory wraps them, not the other way around.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

# Stable namespace for deriving deterministic render job IDs from factory run IDs.
_FACTORY_RENDER_NS = uuid.UUID("6ba7b812-9dad-11d1-80b4-00c04fd430ca")

from sqlalchemy.orm import Session

from app.factory.factory_context import FactoryContext
from app.factory.factory_memory import record_memory
from app.factory.factory_metrics import emit_metric
from app.factory.factory_policy import get_policy_mode, max_stage_retries
from app.factory.factory_router import route_skill
from app.factory.factory_state import (
    GateAction,
    RunStatus,
    STAGE_INDEX,
    STAGE_ORDER,
    StageStatus,
    FactoryStage,
    next_stage,
    percent_complete,
)
from app.factory.factory_validator import evaluate_gate
from app.models.factory_run import (
    FactoryIncident,
    FactoryRun,
    FactoryRunStage,
)


def _to_dict(obj: Any) -> dict[str, Any]:
    """Coerce a service result to a plain dict."""
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "__dict__"):
        return vars(obj)
    return {"raw": str(obj)}

logger = logging.getLogger(__name__)


class FactoryOrchestrator:
    """Drives a FactoryContext through all 12 pipeline stages."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.policy_mode = get_policy_mode()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_run(self, ctx: FactoryContext) -> FactoryRun:
        """Persist a new FactoryRun row and pre-create all stage rows."""
        now = datetime.now(timezone.utc)
        run = FactoryRun(
            id=ctx.run_id,
            trace_id=ctx.trace_id,
            project_id=ctx.project_id,
            input_type=ctx.input_type,
            input_topic=ctx.input_topic,
            input_script=ctx.input_script,
            input_avatar_id=ctx.input_avatar_id,
            input_series_id=ctx.input_series_id,
            status=RunStatus.PENDING.value,
            current_stage=FactoryStage.INTAKE.value,
            percent_complete=0,
            policy_mode=self.policy_mode,
            budget_cents=ctx.budget_cents,
            created_at=now,
        )
        self.db.add(run)

        for stage in STAGE_ORDER:
            stage_row = FactoryRunStage(
                run_id=ctx.run_id,
                stage_name=stage.value,
                stage_index=STAGE_INDEX[stage],
                status=StageStatus.PENDING.value,
            )
            self.db.add(stage_row)

        self.db.commit()
        return run

    def run(self, ctx: FactoryContext) -> dict[str, Any]:
        """Create a run record, then execute the full pipeline."""
        run = self.start_run(ctx)
        return self._run_pipeline(ctx, run)

    def _run_pipeline(self, ctx: FactoryContext, run: FactoryRun) -> dict[str, Any]:
        """Execute the full pipeline against an already-persisted run record."""
        self._update_run(run, status=RunStatus.RUNNING.value, started_at=datetime.now(timezone.utc))

        try:
            for stage in STAGE_ORDER:
                blocked = self._execute_stage(ctx, run, stage)
                if blocked:
                    self._update_run(
                        run,
                        status=RunStatus.FAILED.value,
                        current_stage=stage.value,
                        blocking_reason=f"Quality gate blocked at {stage.value}",
                        completed_at=datetime.now(timezone.utc),
                    )
                    return self._summary(run, success=False)

            # All stages completed
            self._flush_outputs(ctx, run)
            self._write_learning_memory(ctx)
            self._update_run(
                run,
                status=RunStatus.COMPLETED.value,
                current_stage=FactoryStage.TELEMETRY_LEARN.value,
                percent_complete=100,
                completed_at=datetime.now(timezone.utc),
            )
            return self._summary(run, success=True)

        except Exception as exc:  # noqa: BLE001
            logger.exception("Factory run %s failed: %s", ctx.run_id, exc)
            self._record_incident(ctx.run_id, None, "unhandled_exception", str(exc), severity="critical")
            self._update_run(
                run,
                status=RunStatus.FAILED.value,
                error_detail=str(exc),
                completed_at=datetime.now(timezone.utc),
            )
            return self._summary(run, success=False)

    # ------------------------------------------------------------------
    # Stage execution
    # ------------------------------------------------------------------

    def _execute_stage(
        self,
        ctx: FactoryContext,
        run: FactoryRun,
        stage: FactoryStage,
    ) -> bool:
        """Run a single stage with retry logic.  Returns True if blocked."""
        stage_row = (
            self.db.query(FactoryRunStage)
            .filter(
                FactoryRunStage.run_id == ctx.run_id,
                FactoryRunStage.stage_name == stage.value,
            )
            .first()
        )
        if stage_row is None:
            return False  # should not happen

        retries = max_stage_retries(self.policy_mode)
        for attempt in range(retries + 1):
            self._update_stage(stage_row, StageStatus.RUNNING, started_at=datetime.now(timezone.utc))
            self._update_run(
                run,
                current_stage=stage.value,
                percent_complete=percent_complete(stage, StageStatus.RUNNING),
            )

            t0 = time.monotonic()
            try:
                handler = self._get_stage_handler(stage)
                output = handler(ctx)
                duration_ms = int((time.monotonic() - t0) * 1000)

                # Evaluate quality gate for this stage
                gate_action = self._check_gate(ctx, stage, output)
                if gate_action == GateAction.BLOCK:
                    self._update_stage(
                        stage_row,
                        StageStatus.FAILED,
                        completed_at=datetime.now(timezone.utc),
                        duration_ms=duration_ms,
                        output_summary=json.dumps(output)[:2000] if output else None,
                        error_detail="Quality gate blocked",
                    )
                    return True  # blocked

                emit_metric(self.db, ctx.run_id, stage.value, "duration_ms", duration_ms, "ms")
                ctx.set_stage_output(stage.value, output)
                self._update_stage(
                    stage_row,
                    StageStatus.DONE,
                    completed_at=datetime.now(timezone.utc),
                    duration_ms=duration_ms,
                    output_summary=json.dumps(output)[:2000] if output else None,
                )
                return False  # success

            except Exception as exc:  # noqa: BLE001
                duration_ms = int((time.monotonic() - t0) * 1000)
                logger.warning(
                    "Stage %s attempt %d/%d failed: %s",
                    stage.value, attempt + 1, retries + 1, exc,
                )
                stage_row.retry_count = attempt + 1
                self.db.commit()
                if attempt == retries:
                    self._update_stage(
                        stage_row,
                        StageStatus.FAILED,
                        completed_at=datetime.now(timezone.utc),
                        duration_ms=duration_ms,
                        error_detail=str(exc),
                    )
                    self._record_incident(
                        ctx.run_id, stage.value, "stage_failure", str(exc)
                    )
                    return True  # blocked after all retries

        return False  # unreachable

    def _get_stage_handler(self, stage: FactoryStage):
        """Return the method that handles the given stage."""
        return {
            FactoryStage.INTAKE: self._stage_intake,
            FactoryStage.CONTEXT_LOAD: self._stage_context_load,
            FactoryStage.SKILL_ROUTE: self._stage_skill_route,
            FactoryStage.SCRIPT_PLAN: self._stage_script_plan,
            FactoryStage.SCENE_BUILD: self._stage_scene_build,
            FactoryStage.AVATAR_AUDIO_BUILD: self._stage_avatar_audio_build,
            FactoryStage.RENDER_PLAN: self._stage_render_plan,
            FactoryStage.EXECUTE_RENDER: self._stage_execute_render,
            FactoryStage.QA_VALIDATE: self._stage_qa_validate,
            FactoryStage.SEO_PACKAGE: self._stage_seo_package,
            FactoryStage.PUBLISH: self._stage_publish,
            FactoryStage.TELEMETRY_LEARN: self._stage_telemetry_learn,
        }[stage]

    # ------------------------------------------------------------------
    # Stage adapters (thin wrappers around existing services)
    # ------------------------------------------------------------------

    def _stage_intake(self, ctx: FactoryContext) -> dict:
        text = ctx.input_topic or ctx.input_script or ""
        return {"accepted": True, "input_length": len(text)}

    def _stage_context_load(self, ctx: FactoryContext) -> dict:
        """Load historical memory / project context."""
        from app.factory.factory_memory import load_recent_memory

        winner_dna = load_recent_memory(self.db, "winner_dna", limit=3)
        seo_dna = load_recent_memory(self.db, "seo_dna", limit=3)
        ctx.context_data = {
            "winner_dna": winner_dna,
            "seo_dna": seo_dna,
        }
        return ctx.context_data

    def _stage_skill_route(self, ctx: FactoryContext) -> dict:
        skill = route_skill(ctx)
        ctx.selected_skill = skill
        return {"skill": skill}

    def _stage_script_plan(self, ctx: FactoryContext) -> dict:
        """Generate the script plan via AutopilotBrainRuntime."""
        try:
            from app.services.autopilot_brain_runtime import AutopilotBrainRuntime
            from app.schemas.autopilot_brain import AutopilotBrainCompileRequest

            req = AutopilotBrainCompileRequest(
                topic=ctx.input_topic,
                script_text=ctx.input_script,
                platform="youtube",
                store_if_winner=True,
            )
            brain = AutopilotBrainRuntime()
            resp = brain.compile(db=self.db, req=req)
            seo = resp.seo_bridge
            ctx.script_plan = {
                "title": seo.title,
                "hook": seo.description[:120] if seo.description else "",
                "voiceover_script": ctx.input_script or ctx.input_topic or "",
                "scene_count": max(len(resp.series_map), 3),
                "retention_map": [ep.model_dump() for ep in resp.series_map],
                "visual_prompt_plan": [],
                "skill": ctx.selected_skill,
                "decision": resp.scorecard.decision,
                "scorecard": resp.scorecard.model_dump(),
                "seo_bridge": seo.model_dump(),
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("script_plan brain compile failed (%s), using fallback", exc)
            text = ctx.input_script or ctx.input_topic or ""
            ctx.script_plan = {
                "title": text[:80] if text else "Untitled",
                "hook": "",
                "voiceover_script": text,
                "scene_count": 3,
                "retention_map": [],
                "visual_prompt_plan": [],
                "skill": ctx.selected_skill,
                "decision": "TEST",
            }
        return ctx.script_plan

    def _stage_scene_build(self, ctx: FactoryContext) -> dict:
        """Build scene list via StoryboardEngine."""
        text = ctx.input_script or ctx.input_topic or ""
        try:
            from app.services.storyboard_engine import StoryboardEngine

            engine = StoryboardEngine()
            result = engine.generate_from_script(
                script_text=text,
                platform="youtube",
                avatar_id=ctx.input_avatar_id,
                db=self.db,
            )
            ctx.scenes = [
                {
                    "scene_index": s.scene_index,
                    "voiceover": s.voice_direction or s.title,
                    "visual_prompt": s.title,
                    "avatar_instruction": f"emotion={s.emotion or 'neutral'}",
                    "camera_instruction": s.shot_hint or "medium_shot",
                    "duration": round(s.pacing_weight * 5.0, 1),
                    "subtitle_text": s.title,
                    "dependency_reason": s.scene_goal,
                    "visual_type": s.visual_type,
                    "status": "pending",
                }
                for s in result.scenes
            ]
        except Exception as exc:  # noqa: BLE001
            logger.warning("scene_build storyboard failed (%s), using fallback", exc)
            n = (ctx.script_plan or {}).get("scene_count", 3)
            ctx.scenes = [
                {
                    "scene_index": i,
                    "voiceover": text[i * 80 : (i + 1) * 80] if text else "",
                    "visual_prompt": f"Scene {i + 1}",
                    "avatar_instruction": "emotion=neutral",
                    "camera_instruction": "medium_shot",
                    "duration": 5.0,
                    "subtitle_text": f"Scene {i + 1}",
                    "dependency_reason": "sequential",
                    "status": "pending",
                }
                for i in range(n)
            ]
        return {"scene_count": len(ctx.scenes), "scenes": ctx.scenes}

    def _stage_avatar_audio_build(self, ctx: FactoryContext) -> dict:
        """Build avatar/audio resources.  Dispatches a narration job if available."""
        ctx.avatar_id = ctx.input_avatar_id or "default_avatar"
        voice_job_id: str | None = None
        subtitle_url: str | None = None
        duration_ms: int | None = None

        try:
            from app.services.audio.audio_mix_service import create_audio_render_output

            script_text = ctx.input_script or ctx.input_topic or ""
            if script_text:
                audio_out = create_audio_render_output(
                    db=self.db,
                    run_id=ctx.run_id,
                    script_text=script_text,
                    voice_profile_id=ctx.avatar_id,
                )
                ctx.audio_url = getattr(audio_out, "output_url", None)
                voice_job_id = getattr(audio_out, "id", None)
                duration_ms = getattr(audio_out, "duration_ms", None)
        except Exception as exc:  # noqa: BLE001
            logger.warning("avatar_audio_build audio service failed (%s), continuing without audio", exc)
            ctx.audio_url = None

        return {
            "avatar_id": ctx.avatar_id,
            "audio_url": ctx.audio_url,
            "voice_job_id": voice_job_id,
            "subtitle_url": subtitle_url,
            "duration_ms": duration_ms,
        }

    def _stage_render_plan(self, ctx: FactoryContext) -> dict:
        """Build the render execution plan from available scene/budget context."""
        scene_count = len(ctx.scenes)
        budget_cents = ctx.budget_cents or 0
        cost_per_scene = max(1, budget_cents // max(scene_count, 1))

        # Attempt decision-engine enrichment when project context is available
        selected_strategy = "full_rebuild"
        warnings: list[str] = []
        if ctx.project_id and ctx.scenes:
            try:
                from app.render.decision.unified_rebuild_decision_engine import (
                    UnifiedRebuildDecisionEngine,
                )

                engine = UnifiedRebuildDecisionEngine()
                decision = engine.decide(
                    project_id=ctx.project_id,
                    episode_id=ctx.run_id,
                    changed_scene_id=str(ctx.scenes[0].get("scene_index", 0)),
                    change_type="new_content",
                    budget_policy="balanced",
                    force_full_rebuild=True,
                )
                selected_strategy = decision.get("selected_strategy", selected_strategy)
                warnings = decision.get("warnings", [])
            except Exception as exc:  # noqa: BLE001
                logger.warning("render_plan decision engine failed (%s), using defaults", exc)

        ctx.render_plan = {
            "provider": "auto",
            "scene_count": scene_count,
            "avatar_id": ctx.avatar_id,
            "selected_strategy": selected_strategy,
            "affected_scenes": list(range(scene_count)),
            "mandatory_scenes": list(range(scene_count)),
            "estimated_cost": {"cents": budget_cents, "per_scene": cost_per_scene},
            "estimated_time": {"seconds": scene_count * 30},
            "warnings": warnings,
        }
        return ctx.render_plan

    def _stage_execute_render(self, ctx: FactoryContext) -> dict:
        """Create a render job and dispatch the Celery render task."""
        # Always generate an idempotent job ID for this run
        render_job_id = str(uuid.uuid5(_FACTORY_RENDER_NS, f"factory:{ctx.run_id}"))
        ctx.render_job_id = render_job_id

        dispatched = False
        if ctx.project_id:
            try:
                from app.models.render_job import RenderJob
                from app.workers.render_tasks import render_dispatch_task

                # Upsert a minimal render job record if absent
                existing = (
                    self.db.query(RenderJob)
                    .filter(RenderJob.id == render_job_id)
                    .first()
                )
                if existing is None:
                    job_row = RenderJob(
                        id=render_job_id,
                        project_id=ctx.project_id,
                        provider="auto",
                        status="queued",
                    )
                    self.db.add(job_row)
                    self.db.commit()

                render_dispatch_task.delay(render_job_id)
                dispatched = True
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "execute_render dispatch failed (%s), job_id=%s recorded without dispatch",
                    exc, render_job_id,
                )

        return {
            "render_job_id": render_job_id,
            "status": "dispatched" if dispatched else "queued",
            "dispatched": dispatched,
        }

    def _stage_qa_validate(self, ctx: FactoryContext) -> dict:
        """Run quality gates on pipeline outputs."""
        issues: list[str] = []

        # Scene count check
        scene_count = len(ctx.scenes)
        if scene_count == 0:
            issues.append("no_scenes_built")

        # Render job must exist
        if not ctx.render_job_id:
            issues.append("no_render_job_id")

        # Script plan must have a title
        plan = ctx.script_plan or {}
        if not plan.get("title"):
            issues.append("missing_script_title")

        # SEO bridge decision must not be BLOCK
        if plan.get("decision") == "BLOCK":
            issues.append("brain_decision_block")

        # Avatar must be assigned
        if not ctx.avatar_id:
            issues.append("no_avatar_assigned")

        # Render plan must exist and have scenes
        render_plan = ctx.render_plan or {}
        if not render_plan.get("scene_count"):
            issues.append("empty_render_plan")

        ctx.qa_passed = len(issues) == 0
        result = {
            "qa_passed": ctx.qa_passed,
            "scene_count": scene_count,
            "issues": issues,
        }
        if issues:
            result["retry_strategy"] = "downgrade" if len(issues) <= 2 else "human_review"
        return result

    def _stage_seo_package(self, ctx: FactoryContext) -> dict:
        """Generate SEO package via PostRenderSEOOrchestrator."""
        plan = ctx.script_plan or {}
        try:
            from app.services.post_render_seo_orchestrator import PostRenderSEOOrchestrator

            orchestrator = PostRenderSEOOrchestrator()
            pkg = orchestrator.generate_seo_package(
                job=type("J", (), {
                    "id": ctx.run_id,
                    "title": plan.get("title", ""),
                    "project_id": ctx.project_id,
                    "provider_job_id": ctx.render_job_id,
                    "final_video_url": ctx.output_video_url,
                })(),
                project={
                    "title": plan.get("title", ""),
                    "series_id": ctx.input_series_id,
                    "avatar_id": ctx.avatar_id,
                    "scenes": ctx.scenes,
                    "hook": plan.get("hook", ""),
                } if plan else None,
            )
            ctx.seo_package = _to_dict(pkg)
            # Enrich with brain SEO bridge if available
            seo_bridge = plan.get("seo_bridge") or {}
            if seo_bridge and not ctx.seo_package.get("hashtags_video"):
                ctx.seo_package.setdefault("hashtags_video", seo_bridge.get("video_hashtags", []))
                ctx.seo_package.setdefault("hashtags_channel", seo_bridge.get("channel_hashtags", []))
        except Exception:  # noqa: BLE001
            ctx.seo_package = {"title": plan.get("title", ""), "generated": False}
        return ctx.seo_package

    def _stage_publish(self, ctx: FactoryContext) -> dict:
        """Build the publish payload.  Live upload requires explicit approval."""
        import os

        dry_run = os.environ.get("FACTORY_PUBLISH_DRY_RUN", "1") != "0"
        seo = ctx.seo_package or {}
        payload = {
            "run_id": ctx.run_id,
            "render_job_id": ctx.render_job_id,
            "title": seo.get("title") or (ctx.script_plan or {}).get("title", ""),
            "description": seo.get("description", ""),
            "tags": seo.get("hashtags_video", []),
            "video_url": ctx.output_video_url,
            "dry_run": dry_run,
        }
        if dry_run:
            ctx.publish_result = {"status": "dry_run", **payload}
        else:
            # Live publish: future YouTube / provider integration
            ctx.publish_result = {"status": "scheduled", **payload}
        return ctx.publish_result

    def _stage_telemetry_learn(self, ctx: FactoryContext) -> dict:
        summary = {
            "run_id": ctx.run_id,
            "skill": ctx.selected_skill,
            "qa_passed": ctx.qa_passed,
            "render_job_id": ctx.render_job_id,
        }
        ctx.learning_memory = summary
        return summary

    # ------------------------------------------------------------------
    # Quality gate check (per stage)
    # ------------------------------------------------------------------

    STAGE_GATES: dict[str, tuple[str, int]] = {
        FactoryStage.SCRIPT_PLAN.value: ("script_gate", 60),
        FactoryStage.SCENE_BUILD.value: ("scene_gate", 60),
        FactoryStage.AVATAR_AUDIO_BUILD.value: ("avatar_gate", 60),
        FactoryStage.QA_VALIDATE.value: ("render_gate", 70),
        FactoryStage.SEO_PACKAGE.value: ("seo_gate", 60),
        FactoryStage.PUBLISH.value: ("publish_gate", 60),
    }

    def _check_gate(
        self,
        ctx: FactoryContext,
        stage: FactoryStage,
        output: dict | None,
    ) -> GateAction:
        gate_spec = self.STAGE_GATES.get(stage.value)
        if gate_spec is None:
            return GateAction.NONE

        gate_name, threshold = gate_spec
        # Derive a simple score from output completeness
        score = 100 if output else 0

        return evaluate_gate(
            self.db,
            run_id=ctx.run_id,
            stage_name=stage.value,
            gate_name=gate_name,
            score=score,
            threshold=threshold,
            policy_mode=self.policy_mode,
        )

    # ------------------------------------------------------------------
    # Learning memory
    # ------------------------------------------------------------------

    def _write_learning_memory(self, ctx: FactoryContext) -> None:
        if ctx.selected_skill:
            record_memory(self.db, ctx.run_id, "winner_dna", {
                "skill": ctx.selected_skill,
                "topic": ctx.input_topic,
                "qa_passed": ctx.qa_passed,
            })
        if ctx.seo_package:
            record_memory(self.db, ctx.run_id, "seo_dna", ctx.seo_package)
        if not ctx.qa_passed:
            record_memory(self.db, ctx.run_id, "failure_dna", {
                "run_id": ctx.run_id,
                "topic": ctx.input_topic,
                "qa_passed": ctx.qa_passed,
            })

    # ------------------------------------------------------------------
    # ORM helpers
    # ------------------------------------------------------------------

    def _update_run(self, run: FactoryRun, **kwargs: Any) -> None:
        kwargs["updated_at"] = datetime.now(timezone.utc)
        for k, v in kwargs.items():
            if hasattr(run, k):
                val = v.value if hasattr(v, "value") else v
                setattr(run, k, val)
        self.db.commit()

    def _update_stage(
        self,
        stage_row: FactoryRunStage,
        status: StageStatus,
        **kwargs: Any,
    ) -> None:
        stage_row.status = status.value
        for k, v in kwargs.items():
            if hasattr(stage_row, k):
                setattr(stage_row, k, v)
        self.db.commit()

    def _flush_outputs(self, ctx: FactoryContext, run: FactoryRun) -> None:
        run.render_job_id = ctx.render_job_id
        run.output_video_url = ctx.output_video_url
        run.output_thumbnail_url = ctx.output_thumbnail_url
        if ctx.seo_package:
            run.seo_title = (ctx.seo_package.get("title") or "")[:255]
            run.seo_description = ctx.seo_package.get("description") or ""
        if ctx.publish_result:
            run.publish_payload_json = json.dumps(ctx.publish_result)
        self.db.commit()

    def _record_incident(
        self,
        run_id: str,
        stage_name: str | None,
        incident_type: str,
        detail: str,
        severity: str = "error",
    ) -> None:
        incident = FactoryIncident(
            run_id=run_id,
            stage_name=stage_name,
            severity=severity,
            incident_type=incident_type,
            detail=detail[:4000] if detail else None,
            occurred_at=datetime.now(timezone.utc),
        )
        self.db.add(incident)
        self.db.commit()

    def _summary(self, run: FactoryRun, success: bool) -> dict[str, Any]:
        return {
            "run_id": run.id,
            "trace_id": run.trace_id,
            "status": run.status,
            "current_stage": run.current_stage,
            "percent_complete": run.percent_complete,
            "success": success,
            "render_job_id": run.render_job_id,
            "output_video_url": run.output_video_url,
            "seo_title": run.seo_title,
        }
