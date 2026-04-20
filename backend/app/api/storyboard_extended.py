"""Extended storyboard API endpoints — episode ladder and asset manifest."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.storyboard_engine import EpisodeLadderMemory, StoryboardEngine

router = APIRouter(prefix="/api/v1/storyboards", tags=["storyboards"])


class EpisodeLadderItem(BaseModel):
    series_id: str
    episode_index: int
    storyboard_id: str | None = None
    series_arc: str = ""
    character_flags: list[str] = []
    plot_hooks: list[str] = []
    open_loops: list[str] = []
    resolved_loops: list[str] = []


class AssetManifestItem(BaseModel):
    scene_index: int
    scene_goal: str
    avatar_id: str | None = None
    background: str
    avatar_pose: str
    avatar_outfit: str
    video_clip_type: str
    prop_list: list[str]
    text_overlay: bool
    missing_assets: bool
    broll_category: str | None = None
    voice_direction: str | None = None
    shot_hint: str | None = None


@router.get("/series/{series_id}/episode-ladder", response_model=list[EpisodeLadderItem])
def get_episode_ladder(
    series_id: str,
    db: Session = Depends(get_db),
) -> list[EpisodeLadderItem]:
    """Return the ordered episode ladder for a series."""
    memory = EpisodeLadderMemory()
    episodes = memory.load_ladder(db, series_id)
    if not episodes:
        raise HTTPException(
            status_code=404,
            detail=f"No episodes found for series '{series_id}'",
        )
    return [
        EpisodeLadderItem(
            series_id=ep["series_id"],
            episode_index=ep["episode_index"],
            storyboard_id=ep.get("storyboard_id"),
            series_arc=ep.get("series_arc", ""),
            character_flags=ep.get("character_flags", []),
            plot_hooks=ep.get("plot_hooks", []),
            open_loops=ep.get("open_loops", []),
            resolved_loops=ep.get("resolved_loops", []),
        )
        for ep in episodes
    ]


@router.get("/{storyboard_id}/asset-manifest", response_model=list[AssetManifestItem])
def get_asset_manifest(
    storyboard_id: str,
    db: Session = Depends(get_db),
) -> list[AssetManifestItem]:
    """Return the full asset manifest for a storyboard.

    Looks up scenes from the pattern library for this storyboard and generates
    the production checklist.
    """
    try:
        from app.services.pattern_library import PatternLibrary

        lib = PatternLibrary()
        patterns = lib.list(db, pattern_type="scene_pattern")
        scenes_data = [
            p.payload for p in patterns
            if p.source_id == storyboard_id and p.payload
        ]
    except Exception:
        scenes_data = []

    if not scenes_data:
        raise HTTPException(
            status_code=404,
            detail=f"No scenes found for storyboard '{storyboard_id}'",
        )

    # Build synthetic StoryboardScene objects for plan_shot_assets
    from app.schemas.storyboard import StoryboardScene

    scenes = [
        StoryboardScene(
            scene_index=i + 1,
            title=d.get("scene_goal", "scene"),
            scene_goal=d.get("scene_goal", "body"),
            visual_type=d.get("visual_type", ""),
            emotion=d.get("emotion", ""),
            cta_flag=d.get("scene_goal") == "cta",
            open_loop_flag=False,
            shot_hint=d.get("shot_hint"),
            pacing_weight=float(d.get("pacing_weight", 1.0)),
            voice_direction=d.get("voice_direction"),
            transition_hint=d.get("transition_hint"),
        )
        for i, d in enumerate(scenes_data)
    ]

    engine = StoryboardEngine()
    manifest = engine.plan_shot_assets(scenes)

    return [
        AssetManifestItem(
            scene_index=item["scene_index"],
            scene_goal=item["scene_goal"],
            avatar_id=item.get("avatar_id"),
            background=item.get("background", item.get("background_type", "")),
            avatar_pose=item["avatar_pose"],
            avatar_outfit=item.get("avatar_outfit", "natural"),
            video_clip_type=item.get("video_clip_type", "talking_head"),
            prop_list=item.get("prop_list", []),
            text_overlay=bool(item.get("text_overlay", item.get("overlay_text", False))),
            missing_assets=bool(item.get("missing_assets", False)),
            broll_category=item.get("broll_category"),
            voice_direction=item.get("voice_direction"),
            shot_hint=item.get("shot_hint"),
        )
        for item in manifest
    ]
