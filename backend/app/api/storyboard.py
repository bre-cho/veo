from __future__ import annotations

from fastapi import APIRouter

from app.schemas.storyboard import (
    StoryboardGenerateRequest,
    StoryboardGenerateResponse,
    SceneBeatOut,
)
from app.services.storyboard_engine import StoryboardEngine

router = APIRouter(prefix="/api/v1/storyboard", tags=["storyboard"])

_storyboard_engine = StoryboardEngine()


@router.post("/generate", response_model=StoryboardGenerateResponse)
def generate_storyboard(req: StoryboardGenerateRequest):
    """Convert a raw script into a structured storyboard of scene beats."""
    beats = _storyboard_engine.parse_script(req.script, max_scenes=req.max_scenes)
    return StoryboardGenerateResponse(
        scene_count=len(beats),
        scenes=[SceneBeatOut(**b.to_dict()) for b in beats],
    )
