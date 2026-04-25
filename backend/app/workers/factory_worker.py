"""Celery worker task for executing a FactoryRun end-to-end."""
from __future__ import annotations

import logging

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.factory.factory_context import FactoryContext
from app.factory.factory_orchestrator import FactoryOrchestrator
from app.factory.factory_state import RunStatus
from app.models.factory_run import FactoryRun

logger = logging.getLogger(__name__)


@celery_app.task(name="factory.run", bind=True, max_retries=0)
def factory_run_task(self, run_id: str) -> dict:
    """Execute all 12 factory stages for the given run_id."""
    db = SessionLocal()
    try:
        run = db.query(FactoryRun).filter(FactoryRun.id == run_id).first()
        if run is None:
            logger.error("factory_run_task: run %s not found", run_id)
            return {"error": "run_not_found", "run_id": run_id}

        if run.status not in (RunStatus.PENDING.value, RunStatus.RUNNING.value):
            logger.info("factory_run_task: run %s already in status %s, skipping", run_id, run.status)
            return {"skipped": True, "status": run.status}

        # Reconstruct context from persisted run
        ctx = FactoryContext(
            run_id=run.id,
            trace_id=run.trace_id or run.id,
            project_id=run.project_id,
            input_type=run.input_type,
            input_topic=run.input_topic,
            input_script=run.input_script,
            input_avatar_id=run.input_avatar_id,
            input_series_id=run.input_series_id,
            policy_mode=run.policy_mode,
            budget_cents=run.budget_cents,
        )

        orchestrator = FactoryOrchestrator(db)
        # Skip start_run (already called by API) – go straight to pipeline
        result = orchestrator._run_pipeline(ctx, run)
        return result
    finally:
        db.close()
