from __future__ import annotations

from fastapi import APIRouter

from app.schemas.storyboard import StoryboardRequest, StoryboardResponse
from app.services.storyboard_engine import StoryboardEngine

router = APIRouter(prefix="/api/v1/storyboard", tags=["storyboard"])

_engine = StoryboardEngine()


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
