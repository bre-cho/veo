from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
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
def generate_storyboard(
    req: StoryboardRequest,
    include_asset_plan: bool = Query(default=False),
    use_winning_graph: bool = Query(default=False),
    avatar_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> StoryboardResponse:
    """Generate a storyboard from script text.

    Phase 4.2: Pass ``include_asset_plan=true`` to receive per-scene asset plans.
    Phase 4.4: Pass ``use_winning_graph=true`` to seed scenes from top winning graph.
    """
    text = req.script_text or (req.preview_payload or {}).get("script_text") or ""
    learning_store = PerformanceLearningEngine(db=db)
    return _engine.generate_from_script(
        script_text=text,
        conversion_mode=req.conversion_mode,
        content_goal=req.content_goal,
        preview_payload=req.preview_payload,
        learning_store=learning_store,
        use_winning_graph=use_winning_graph,
        include_asset_plan=include_asset_plan,
        avatar_id=avatar_id,
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
    """Generate the next episode storyboard with continuity hints from the previous one."""
    hints = _continuity_planner.plan_continuity(req.prev_storyboard, req.next_script)

    episode_memory: dict[str, Any] | None = None
    if req.series_id:
        episode_memory = _continuity_planner.load_latest_episode(db, req.series_id)

    prev_summary: dict[str, Any] = req.prev_storyboard.summary or {}
    platform: str | None = prev_summary.get("platform") or None

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


# ---------------------------------------------------------------------------
# Phase 4.3: Series memory endpoint
# ---------------------------------------------------------------------------


@router.get("/series/{series_id}/memory", response_model=dict)
def get_series_memory(series_id: str, db: Session = Depends(get_db)) -> dict:
    """Return series-level memory aggregation for a storyboard series.

    Phase 4.3: Returns all episode memories for the series, including
    winning_scene_sequence, series_arc, and character_callbacks.
    """
    from app.models.episode_memory import EpisodeMemory

    memories = (
        db.query(EpisodeMemory)
        .filter(EpisodeMemory.series_id == series_id)
        .order_by(EpisodeMemory.episode_index)
        .all()
    )
    if not memories:
        return {"series_id": series_id, "episode_count": 0, "episodes": []}

    episodes = [
        {
            "episode_index": m.episode_index,
            "storyboard_id": m.storyboard_id,
            "open_loops": m.open_loops,
            "resolved_loops": m.resolved_loops,
            "winning_scene_sequence": m.winning_scene_sequence,
            "series_arc": m.series_arc,
            "character_callbacks": m.character_callbacks,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in memories
    ]
    return {
        "series_id": series_id,
        "episode_count": len(episodes),
        "episodes": episodes,
        "latest_open_loops": memories[-1].open_loops if memories else [],
        "latest_winning_sequence": memories[-1].winning_scene_sequence if memories else None,
    }


# ---------------------------------------------------------------------------
# Phase 4.4: Winning scene graphs endpoint
# ---------------------------------------------------------------------------


@router.get("/winning-graphs", response_model=dict)
def get_winning_graphs(
    platform: str | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
) -> dict:
    """Return top winning scene graphs sorted by conversion_score descending.

    Phase 4.4: Used for seeding new storyboard generation.
    """
    from app.services.storyboard.winning_scene_graph_store import WinningSceneGraphStore

    store = WinningSceneGraphStore(db=db)
    graphs = store.get_top_graphs(platform=platform, limit=limit)
    return {
        "platform": platform,
        "count": len(graphs),
        "winning_graphs": graphs,
    }


@router.post("/winning-graphs/record", response_model=dict)
def record_winning_graph(
    storyboard_id: str,
    conversion_score: float,
    platform: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """Manually record a winning scene graph for a storyboard.

    Phase 4.4: Used when conversion_score is reported externally.
    """
    from app.services.storyboard.winning_scene_graph_store import WinningSceneGraphStore

    store = WinningSceneGraphStore(db=db)
    persisted = store.record_winning_graph(
        storyboard_id=storyboard_id,
        platform=platform,
        conversion_score=conversion_score,
    )
    return {"ok": True, "persisted": persisted, "storyboard_id": storyboard_id}

