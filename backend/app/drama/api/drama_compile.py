from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

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
