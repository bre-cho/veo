from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.storyboard import StoryboardRequest, StoryboardResponse
from app.services.learning_engine import PerformanceLearningEngine
from app.services.storyboard_engine import ContinuityPlanner, StoryboardEngine

router = APIRouter(prefix="/api/v1/storyboard", tags=["storyboard"])

_engine = StoryboardEngine()
_continuity_planner = ContinuityPlanner()


@router.post("/generate", response_model=StoryboardResponse)
def generate_storyboard(req: StoryboardRequest) -> StoryboardResponse:
    text = req.script_text or (req.preview_payload or {}).get("script_text") or ""
    return _engine.generate_from_script(
        script_text=text,
        conversion_mode=req.conversion_mode,
        content_goal=req.content_goal,
        preview_payload=req.preview_payload,
    )


@router.post("/from-preview", response_model=StoryboardResponse)
def storyboard_from_preview(preview_payload: dict) -> StoryboardResponse:
    return _engine.generate_from_preview(preview_payload)


# ---------------------------------------------------------------------------
# Continuity endpoint
# ---------------------------------------------------------------------------

class ContinuityRequest(BaseModel):
    prev_storyboard: StoryboardResponse
    next_script: str = Field(..., min_length=1)
    series_id: str | None = None
    episode_index: int | None = None
    save_episode_memory: bool = False


class ContinuityResponse(BaseModel):
    continuity_hints: list[str]
    storyboard: StoryboardResponse


@router.post("/continuity", response_model=ContinuityResponse)
def plan_continuity(req: ContinuityRequest, db: Session = Depends(get_db)) -> ContinuityResponse:
    """Generate the next episode storyboard with continuity hints from the previous one.

    Platform grammar and performance learning are now forwarded to
    ``generate_from_script`` so the new episode benefits from:
    - The same platform's hook/pacing grammar as the previous episode.
    - Live performance feedback from ``PerformanceLearningEngine``.
    """
    hints = _continuity_planner.plan_continuity(req.prev_storyboard, req.next_script)

    episode_memory: dict[str, Any] | None = None
    if req.series_id:
        episode_memory = _continuity_planner.load_latest_episode(db, req.series_id)

    # Extract platform from the previous storyboard's summary so the new
    # episode inherits the correct platform grammar.
    prev_summary: dict[str, Any] = req.prev_storyboard.summary or {}
    platform: str | None = prev_summary.get("platform") or None

    # Instantiate a learning store backed by the current DB session so
    # platform-specific hook/pacing boosts are applied to the new episode.
    learning_store = PerformanceLearningEngine(db=db)

    new_storyboard = _engine.generate_from_script(
        script_text=req.next_script,
        episode_memory=episode_memory,
        platform=platform,
        learning_store=learning_store,
    )

    if req.save_episode_memory and req.series_id and req.episode_index is not None:
        _continuity_planner.save_episode_memory(
            db,
            series_id=req.series_id,
            episode_index=req.episode_index,
            storyboard=new_storyboard,
        )

    return ContinuityResponse(continuity_hints=hints, storyboard=new_storyboard)


# ---------------------------------------------------------------------------
# Shot asset planner endpoint
# ---------------------------------------------------------------------------

class ShotAssetRequest(BaseModel):
    storyboard: StoryboardResponse
    avatar_id: str | None = None


@router.post("/shot-assets")
def plan_shot_assets(req: ShotAssetRequest) -> dict:
    """Return a production asset checklist for each scene in the storyboard."""
    checklist = StoryboardEngine.plan_shot_assets(req.storyboard.scenes, avatar_id=req.avatar_id)
    return {"scene_count": len(checklist), "assets": checklist}

