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
        """Generate or validate the script plan."""
        text = ctx.input_script or ctx.input_topic or ""
        ctx.script_plan = {
            "title": text[:80] if text else "Untitled",
            "scenes_estimate": 3,
            "skill": ctx.selected_skill,
        }
        return ctx.script_plan

    def _stage_scene_build(self, ctx: FactoryContext) -> dict:
        """Build scene list from script plan."""
        n = (ctx.script_plan or {}).get("scenes_estimate", 3)
        ctx.scenes = [{"scene_index": i, "status": "pending"} for i in range(n)]
        return {"scene_count": len(ctx.scenes)}

    def _stage_avatar_audio_build(self, ctx: FactoryContext) -> dict:
        ctx.avatar_id = ctx.input_avatar_id or "default_avatar"
        ctx.audio_url = None  # real impl calls audio service
        return {"avatar_id": ctx.avatar_id, "audio_url": ctx.audio_url}

    def _stage_render_plan(self, ctx: FactoryContext) -> dict:
        ctx.render_plan = {
            "provider": "auto",
            "scene_count": len(ctx.scenes),
            "avatar_id": ctx.avatar_id,
        }
        return ctx.render_plan

    def _stage_execute_render(self, ctx: FactoryContext) -> dict:
        """Dispatch render job (stub; real impl enqueues Celery task)."""
        ctx.render_job_id = str(uuid.uuid4())
        return {"render_job_id": ctx.render_job_id, "status": "dispatched"}

    def _stage_qa_validate(self, ctx: FactoryContext) -> dict:
        ctx.qa_passed = True  # real impl checks render output
        return {"qa_passed": ctx.qa_passed}

    def _stage_seo_package(self, ctx: FactoryContext) -> dict:
        """Generate SEO package via PostRenderSEOOrchestrator."""
        try:
            from app.services.post_render_seo_orchestrator import PostRenderSEOOrchestrator

            orchestrator = PostRenderSEOOrchestrator()
            # Pass minimal stub objects; real impl passes live job/project
            pkg = orchestrator.generate_seo_package(
                job=type("J", (), {
                    "id": ctx.run_id,
                    "title": (ctx.script_plan or {}).get("title", ""),
                    "project_id": ctx.project_id,
                    "provider_job_id": ctx.render_job_id,
                })(),
                project=None,
            )
            ctx.seo_package = _to_dict(pkg)
        except Exception:  # noqa: BLE001
            ctx.seo_package = {"title": (ctx.script_plan or {}).get("title", ""), "generated": False}
        return ctx.seo_package

    def _stage_publish(self, ctx: FactoryContext) -> dict:
        ctx.publish_result = {"status": "scheduled", "run_id": ctx.run_id}
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
