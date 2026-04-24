from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.drama.schemas.scene_drama import (
    SceneDramaAnalyzeRequest,
    SceneDramaAnalyzeResponse,
)
from app.drama.services.scene_drama_service import SceneDramaService

router = APIRouter(prefix="/api/v1/drama/scenes", tags=["drama_scenes"])


@router.post("/analyze", response_model=SceneDramaAnalyzeResponse)
def analyze_scene(
    payload: SceneDramaAnalyzeRequest,
    db: Session = Depends(get_db),
) -> SceneDramaAnalyzeResponse:
    result = SceneDramaService(db).analyze_scene(
        project_id=payload.project_id,
        scene_id=payload.scene_id,
        character_ids=payload.character_ids,
        scene_context=payload.scene_context,
    )
    return SceneDramaAnalyzeResponse(**result)


@router.post("/{scene_id}/compile")
def compile_scene(scene_id: str) -> dict:
    # TODO: connect to prompt/render bridge in phase 3.
    return {
        "scene_id": scene_id,
        "status": "stubbed",
        "message": "Phase 2 compile hook reserved for prompt/render bridge.",
    }
