from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.drama.models.scene_drama_state import DramaSceneState
from app.drama.schemas.compile import (
    CompileEpisodeRequest,
    CompileEpisodeResponse,
    CompileProjectRequest,
    CompileProjectResponse,
)
from app.drama.services.drama_compiler_service import DramaCompilerService

router = APIRouter(prefix="/api/v1/drama/compile", tags=["drama-compile"])
service = DramaCompilerService()


class ParticipantIn(BaseModel):
    character_id: str
    name: Optional[str] = None


class CompileSceneRequest(BaseModel):
    scene_context: Dict[str, Any]
    scene_analysis: Dict[str, Any]
    previous_scene_state: Optional[Dict[str, Any]] = None
    character_arc_state: Optional[Dict[str, Any]] = None


@router.post("/scene")
def compile_scene(request: CompileSceneRequest) -> Dict[str, Any]:
    return service.compile_scene(
        scene_context=request.scene_context,
        scene_analysis=request.scene_analysis,
        previous_scene_state=request.previous_scene_state,
        character_arc_state=request.character_arc_state,
    )


@router.post("/episode", response_model=CompileEpisodeResponse)
def compile_episode(request: CompileEpisodeRequest, db: Session = Depends(get_db)) -> CompileEpisodeResponse:
    rows = (
        db.query(DramaSceneState)
        .filter(DramaSceneState.project_id == request.project_id)
        .filter(DramaSceneState.episode_id == request.episode_id)
        .order_by(DramaSceneState.created_at.asc())
        .all()
    )
    scene_rows = [
        {
            "scene_id": str(row.scene_id),
            "scene_context": {"scene_id": str(row.scene_id)},
            "analysis_payload": row.analysis_payload or {},
        }
        for row in rows
    ]
    compiled = service.compile_episode(scene_rows)
    return CompileEpisodeResponse(
        project_id=request.project_id,
        episode_id=request.episode_id,
        scene_count=compiled["scene_count"],
        compiled_scenes=compiled["compiled_scenes"],
        continuity_warnings=compiled["continuity_warnings"],
    )


@router.post("/project", response_model=CompileProjectResponse)
def compile_project(request: CompileProjectRequest, db: Session = Depends(get_db)) -> CompileProjectResponse:
    rows = (
        db.query(DramaSceneState)
        .filter(DramaSceneState.project_id == request.project_id)
        .order_by(DramaSceneState.episode_id.asc(), DramaSceneState.created_at.asc())
        .all()
    )
    by_episode: dict[str, list[dict]] = {}
    for row in rows:
        key = str(row.episode_id) if row.episode_id else "none"
        by_episode.setdefault(key, []).append(
            {
                "scene_id": str(row.scene_id),
                "scene_context": {"scene_id": str(row.scene_id)},
                "analysis_payload": row.analysis_payload or {},
            }
        )
    episode_rows = [{"episode_id": k, "scenes": v} for k, v in by_episode.items()]
    compiled = service.compile_project(episode_rows)
    return CompileProjectResponse(
        project_id=request.project_id,
        episode_count=compiled["episode_count"],
        scene_count=compiled["scene_count"],
        compiled_scenes=compiled["compiled_scenes"],
        continuity_warnings=compiled["continuity_warnings"],
    )
