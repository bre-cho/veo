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
from app.schemas.brain_manifest import BrainRenderFeedback, BrainPublishFeedback
from app.services.brain.brain_memory_service import BrainMemoryService
from app.services.brain.brain_feedback_service import BrainFeedbackService

router = APIRouter(prefix="/api/v1/brain", tags=["brain-memory"])
_memory_service = BrainMemoryService()
_feedback_service = BrainFeedbackService()


# ── Read endpoints ────────────────────────────────────────────────────────────

@router.get("/memory/patterns")
async def list_brain_patterns(
    pattern_type: str | None = None,
    market_code: str | None = None,
    content_goal: str | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """List top winner patterns from PatternMemory."""
    try:
        from app.services.pattern_library import PatternLibrary
        lib = PatternLibrary()
        if pattern_type:
            rows = lib.list(db, pattern_type=pattern_type, market_code=market_code, content_goal=content_goal)[:limit]
        else:
            rows = lib.list_winners(db, market_code=market_code, content_goal=content_goal, limit=limit)
        return {
            "ok": True,
            "data": [
                {
                    "id": r.id,
                    "pattern_type": r.pattern_type,
                    "score": r.score,
                    "market_code": r.market_code,
                    "content_goal": r.content_goal,
                    "payload": r.payload,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ],
            "meta": {"count": len(rows)},
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to list patterns") from exc


@router.get("/memory/series/{series_id}")
async def get_series_memory(
    series_id: str,
    db: Session = Depends(get_db),
):
    """Return the latest EpisodeMemory for a given series_id."""
    try:
        bundle = _memory_service.recall(db, series_id=series_id)
        return {
            "ok": True,
            "data": {
                "latest_episode_memory": bundle.get("latest_episode_memory"),
                "continuity_context": bundle.get("continuity_context"),
                "winner_dna_summary": bundle.get("winner_dna_summary"),
                "memory_refs": bundle.get("memory_refs"),
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load series memory") from exc


# ── Write endpoints ───────────────────────────────────────────────────────────

@router.post("/feedback/render")
async def feedback_render(
    payload: BrainRenderFeedback,
    db: Session = Depends(get_db),
):
    """Manually trigger a render feedback write to Brain memory."""
    try:
        _feedback_service.record_render_outcome(
            db,
            project_id=payload.project_id,
            render_job_id=payload.render_job_id,
            final_video_url=payload.final_video_url,
            scene_statuses=payload.scene_statuses,
            continuity_context=payload.continuity_context,
            brain_plan=payload.brain_plan,
            winner_dna_summary=payload.winner_dna_summary,
        )
        return {"ok": True, "message": "Render feedback recorded"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to record render feedback") from exc


@router.post("/feedback/publish")
async def feedback_publish(
    payload: BrainPublishFeedback,
    db: Session = Depends(get_db),
):
    """Manually trigger a publish feedback write to Brain memory."""
    try:
        _feedback_service.record_publish_outcome(
            db,
            project_id=payload.project_id,
            publish_job_id=payload.publish_job_id,
            platform=payload.platform,
            title=payload.title,
            description=payload.description,
            thumbnail_url=payload.thumbnail_url,
            signal_metrics=payload.signal_metrics,
        )
        return {"ok": True, "message": "Publish feedback recorded"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to record publish feedback") from exc
