"""API routes for the Unified Rebuild decision/approve/execute pipeline.

Routes
------
POST /api/v1/render/rebuild/decide       → produce a decision payload
POST /api/v1/render/rebuild/approve      → approve and execute the decision
POST /api/v1/render/rebuild/execute      → alias for approve (backward compat)
GET  /api/v1/render/rebuild/{job_id}/audit → return audit trail for a job
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.render.decision.unified_rebuild_decision_engine import UnifiedRebuildDecisionEngine
from app.render.execution.approved_rebuild_executor import (
    ApprovedRebuildExecutor,
    get_default_audit_log,
)

_logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/render/rebuild",
    tags=["render-rebuild"],
)

# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class RebuildDecideRequest(BaseModel):
    project_id: str
    episode_id: str
    changed_scene_id: str
    change_type: str = "subtitle"
    budget_policy: str = "balanced"
    force_full_rebuild: bool = False
    force_quality_rebuild: bool = False
    include_optional_rebuilds: bool = False
    has_timeline_drift: bool = False
    max_rebuild_cost: Optional[float] = None
    max_rebuild_time_sec: Optional[float] = None
    allow_budget_downgrade: Optional[bool] = None


class RebuildApproveRequest(BaseModel):
    """Carry a decision payload to be approved and executed."""

    decision: Dict[str, Any]
    job_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/decide")
def rebuild_decide(req: RebuildDecideRequest) -> Dict[str, Any]:
    """Produce a unified rebuild decision without executing it.

    The caller receives the full decision payload including cost estimates,
    mandatory/optional scene lists, warnings, and budget policy outcome.
    A human operator (or the frontend) can then call ``/approve`` to proceed.
    """
    try:
        engine = UnifiedRebuildDecisionEngine()
        return engine.decide(
            project_id=req.project_id,
            episode_id=req.episode_id,
            changed_scene_id=req.changed_scene_id,
            change_type=req.change_type,
            budget_policy=req.budget_policy,
            force_full_rebuild=req.force_full_rebuild,
            force_quality_rebuild=req.force_quality_rebuild,
            include_optional_rebuilds=req.include_optional_rebuilds,
            has_timeline_drift=req.has_timeline_drift,
            max_rebuild_cost=req.max_rebuild_cost,
            max_rebuild_time_sec=req.max_rebuild_time_sec,
            allow_budget_downgrade=req.allow_budget_downgrade,
        )
    except FileNotFoundError as exc:
        _logger.warning("rebuild_decide: resource not found: %s", exc)
        raise HTTPException(status_code=404, detail="Episode or manifest not found") from exc
    except ValueError as exc:
        _logger.warning("rebuild_decide: bad request: %s", exc)
        raise HTTPException(status_code=422, detail="Invalid rebuild request parameters") from exc
    except Exception as exc:  # noqa: BLE001
        _logger.exception("rebuild_decide: unexpected error")
        raise HTTPException(status_code=500, detail="Rebuild decision failed") from exc


@router.post("/approve")
def rebuild_approve(req: RebuildApproveRequest) -> Dict[str, Any]:
    """Approve and execute a previously produced decision payload.

    Idempotent: re-submitting the same decision returns the cached result.
    """
    try:
        executor = ApprovedRebuildExecutor()
        return executor.execute(decision=req.decision, job_id=req.job_id)
    except Exception as exc:  # noqa: BLE001
        _logger.exception("rebuild_approve: unexpected error")
        raise HTTPException(status_code=500, detail="Rebuild execution failed") from exc


@router.post("/execute")
def rebuild_execute(req: RebuildApproveRequest) -> Dict[str, Any]:
    """Alias for ``/approve`` – kept for backward compatibility."""
    return rebuild_approve(req)


@router.get("/{job_id}/audit")
def rebuild_audit(job_id: str) -> List[Dict[str, Any]]:
    """Return the audit trail for a rebuild job.

    In the default configuration the audit log is in-process memory.
    In production this should be wired to a persistent store.
    """
    log = get_default_audit_log()
    return [entry for entry in log if entry.get("job_id") == job_id]
