"""brain_memory — GET/POST routes for inspecting and updating Brain memory.

Routes:
    GET  /api/v1/brain/memory/patterns
    GET  /api/v1/brain/memory/series/{series_id}
    POST /api/v1/brain/feedback/render
    POST /api/v1/brain/feedback/publish
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.brain_manifest import BrainFeedbackPayload
from app.services.brain.brain_memory_service import BrainMemoryService
from app.services.brain.brain_feedback_service import BrainFeedbackService

router = APIRouter(prefix="/api/v1/brain", tags=["brain-memory"])
_memory = BrainMemoryService()
_feedback_service = BrainFeedbackService()


# ── Read endpoints ────────────────────────────────────────────────────────────

@router.get("/memory/patterns")
async def get_brain_patterns(
    market_code: str | None = None,
    content_goal: str | None = None,
    series_id: str | None = None,
    db: Session = Depends(get_db),
):
    """List top winner patterns from PatternMemory."""
    return {
        "ok": True,
        "data": _memory.recall(
            db,
            market_code=market_code,
            content_goal=content_goal,
            series_id=series_id,
        ),
        "error": None,
    }


@router.get("/memory/series/{series_id}")
async def get_series_memory(
    series_id: str,
    db: Session = Depends(get_db),
):
    """Return the latest EpisodeMemory for a given series_id."""
    try:
        bundle = _memory.recall(db, market_code=None, content_goal=None, series_id=series_id)
        return {
            "ok": True,
            "data": {
                "latest_episode_memory": bundle.get("latest_episode_memory"),
                "winner_dna_summary": bundle.get("winner_dna_summary"),
                "memory_refs": bundle.get("memory_refs"),
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load series memory") from exc


# ── Write endpoints ───────────────────────────────────────────────────────────

@router.post("/feedback/render")
async def feedback_render(
    payload: BrainFeedbackPayload,
    db: Session = Depends(get_db),
):
    """Manually trigger a render feedback write to Brain memory.

    The caller should pass a full project-like payload via the BrainFeedbackPayload
    fields; series_id / episode_index / continuity_context / brain_plan are read
    from the reconstructed project dict.
    """
    try:
        project = {
            "series_id": payload.metrics.get("series_id"),
            "episode_index": payload.metrics.get("episode_index"),
            "continuity_context": payload.metrics.get("continuity_context") or {},
            "brain_plan": payload.metrics.get("brain_plan") or {},
        }
        _feedback_service.record_render_outcome(
            db,
            project=project,
            render_job_id=payload.render_job_id or "",
            final_video_url=payload.final_video_url,
            status=payload.status or "completed",
        )
        return {"ok": True, "message": "Render feedback recorded"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to record render feedback") from exc


@router.post("/feedback/publish")
async def feedback_publish(
    payload: BrainFeedbackPayload,
    db: Session = Depends(get_db),
):
    """Manually trigger a publish feedback write to Brain memory."""
    try:
        _feedback_service.record_publish_outcome(
            db,
            payload=payload.model_dump(),
            score=float(payload.metrics.get("score") or 0.5),
        )
        return {"ok": True, "message": "Publish feedback recorded"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to record publish feedback") from exc
