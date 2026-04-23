"""topic_intake — POST /api/v1/topic-intake/preview

Convert a raw topic into an enriched ScriptPreviewPayload-shaped response via
the Brain Layer (BrainIntakeService.orchestrate_topic_preview).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.brain_intake import TopicPreviewRequest
from app.services.brain.brain_intake_service import BrainIntakeService

router = APIRouter(tags=["brain-intake"])
_brain_intake_service = BrainIntakeService()


@router.post("/api/v1/topic-intake/preview")
async def topic_intake_preview(
    payload: TopicPreviewRequest,
    db: Session = Depends(get_db),
):
    """Generate an enriched preview from a topic (no file upload needed)."""
    try:
        preview = _brain_intake_service.orchestrate_topic_preview(
            db,
            topic=payload.topic,
            aspect_ratio=payload.aspect_ratio,
            target_platform=payload.target_platform,
            style_preset=payload.style_preset,
            avatar_id=payload.avatar_id,
            market_code=payload.market_code,
            content_goal=payload.content_goal,
            conversion_mode=payload.conversion_mode,
            series_id=payload.series_id,
            episode_index=payload.episode_index,
        )
        return {
            "ok": True,
            "data": preview,
            "error": None,
            "meta": {
                "source_mode": "topic_intake",
                "scene_count": len(preview.get("scenes") or []),
                "subtitle_count": len(preview.get("subtitle_segments") or []),
                "series_id": preview.get("series_id"),
                "episode_index": preview.get("episode_index"),
                "episode_role": (preview.get("brain_plan") or {}).get("episode_role"),
            },
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to build topic preview") from exc
