"""Function executor for LLM tool calls.

Each tool in ALLOWED_TOOL_NAMES is wired to a DB-backed handler here.
All executions are:
- Validated against the whitelist.
- Inputs type-checked before DB access.
- Results returned as JSON-serialisable dicts.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.services.llm.function_registry import ALLOWED_TOOL_NAMES

logger = logging.getLogger(__name__)


# ── Individual tool handlers ──────────────────────────────────────────────────


def _tool_get_job_status(db: Session, args: dict[str, Any]) -> dict[str, Any]:
    from app.models.render_job import RenderJob

    job_id = str(args.get("job_id", "")).strip()
    if not job_id:
        return {"error": "job_id is required"}

    job = db.query(RenderJob).filter(RenderJob.id == job_id).first()
    if job is None:
        return {"error": f"Job not found: {job_id}"}

    return {
        "job_id": job.id,
        "project_id": job.project_id,
        "provider": job.provider,
        "status": job.status,
        "planned_scene_count": job.planned_scene_count,
        "completed_scene_count": job.completed_scene_count,
        "failed_scene_count": job.failed_scene_count,
        "health_status": job.health_status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


def _tool_list_recent_jobs(db: Session, args: dict[str, Any]) -> dict[str, Any]:
    from app.models.render_job import RenderJob

    limit = max(1, min(int(args.get("limit", 10)), 50))
    status_filter = args.get("status")

    q = db.query(RenderJob).order_by(RenderJob.created_at.desc())
    if status_filter:
        q = q.filter(RenderJob.status == str(status_filter))
    jobs = q.limit(limit).all()

    return {
        "jobs": [
            {
                "job_id": j.id,
                "project_id": j.project_id,
                "provider": j.provider,
                "status": j.status,
                "planned_scene_count": j.planned_scene_count,
                "completed_scene_count": j.completed_scene_count,
                "failed_scene_count": j.failed_scene_count,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in jobs
        ]
    }


def _tool_get_metrics_snapshot(db: Session, _args: dict[str, Any]) -> dict[str, Any]:
    from app.models.render_job import RenderJob
    from app.models.render_incident_state import RenderIncidentState

    status_counts: dict[str, int] = {}
    for status in ("queued", "submitted", "processing", "merging", "done", "failed", "cancelled"):
        count = db.query(RenderJob).filter(RenderJob.status == status).count()
        if count:
            status_counts[status] = count

    open_incidents = db.query(RenderIncidentState).filter(
        RenderIncidentState.status.in_(["open", "acknowledged", "assigned"])
    ).count()
    critical_incidents = db.query(RenderIncidentState).filter(
        RenderIncidentState.status.in_(["open", "acknowledged", "assigned"]),
        RenderIncidentState.current_severity_rank >= 20,
    ).count()

    return {
        "job_status_counts": status_counts,
        "open_incidents": open_incidents,
        "critical_incidents": critical_incidents,
    }


def _tool_get_job_timeline(db: Session, args: dict[str, Any]) -> dict[str, Any]:
    from app.models.render_timeline_event import RenderTimelineEvent

    job_id = str(args.get("job_id", "")).strip()
    if not job_id:
        return {"error": "job_id is required"}
    limit = max(1, min(int(args.get("limit", 50)), 200))

    events = (
        db.query(RenderTimelineEvent)
        .filter(RenderTimelineEvent.job_id == job_id)
        .order_by(RenderTimelineEvent.occurred_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "job_id": job_id,
        "events": [
            {
                "event_type": e.event_type,
                "status": e.status,
                "provider": e.provider,
                "source": e.source,
                "failure_code": e.failure_code,
                "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
            }
            for e in events
        ],
    }


def _tool_get_decision_engine_recommendations(db: Session, _args: dict[str, Any]) -> dict[str, Any]:
    from app.services.decision_engine import evaluate_decision_policy

    result = evaluate_decision_policy(db)
    return {
        "policy_version": result.policy_version,
        "evaluated_at": result.evaluated_at.isoformat() if result.evaluated_at else None,
        "recommendations": [
            {
                "decision_key": r.decision_key,
                "decision_type": r.decision_type,
                "severity": r.severity,
                "title": r.title,
                "rationale": r.rationale,
            }
            for r in result.recommendations
        ],
    }


# ── Dispatcher ────────────────────────────────────────────────────────────────

_HANDLERS = {
    "get_job_status": _tool_get_job_status,
    "list_recent_jobs": _tool_list_recent_jobs,
    "get_metrics_snapshot": _tool_get_metrics_snapshot,
    "get_job_timeline": _tool_get_job_timeline,
    "get_decision_engine_recommendations": _tool_get_decision_engine_recommendations,
}


def execute_tool(
    db: Session,
    *,
    tool_name: str,
    tool_args: dict[str, Any] | str,
    audit_actor: str = "llm-agent",
) -> dict[str, Any]:
    """Execute a whitelisted tool call.

    Parameters
    ----------
    db          : SQLAlchemy session.
    tool_name   : Must be in ALLOWED_TOOL_NAMES.
    tool_args   : JSON-parsed dict (or JSON string) of tool arguments.
    audit_actor : Label used in audit logging.

    Returns a JSON-serialisable result dict; never raises.
    """
    if tool_name not in ALLOWED_TOOL_NAMES:
        logger.warning("Rejected tool call: %s (not in whitelist)", tool_name)
        return {"error": f"Tool '{tool_name}' is not permitted"}

    if isinstance(tool_args, str):
        try:
            tool_args = json.loads(tool_args)
        except json.JSONDecodeError:
            tool_args = {}

    handler = _HANDLERS.get(tool_name)
    if handler is None:
        return {"error": f"Tool '{tool_name}' has no handler registered"}

    try:
        logger.info("Executing tool %s (actor=%s)", tool_name, audit_actor)
        return handler(db, tool_args)
    except Exception as exc:
        logger.exception("Tool %s raised: %s", tool_name, exc)
        return {"error": f"Tool execution error: {exc}"}
