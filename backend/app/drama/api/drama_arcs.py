from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.drama.engines.arc_engine import ArcEngine
from app.drama.schemas.drama_state import ArcProgressRead
from app.drama.services.arc_service import ArcService

router = APIRouter(prefix="/api/v1/drama/arcs", tags=["drama-arcs"])
engine = ArcEngine()


class AdvanceArcRequest(BaseModel):
    character_arc_state: Dict[str, Any]
    scene_analysis: Dict[str, Any]


class RecomputeArcRequest(BaseModel):
    project_id: UUID
    episode_id: UUID | None = None
    force_recompute: bool = False


@router.post("/advance")
def advance_arc(request: AdvanceArcRequest) -> Dict[str, Any]:
    return engine.advance_arc(
        character_arc_state=request.character_arc_state,
        scene_analysis=request.scene_analysis,
    )


@router.post("/{character_id}/advance")
def advance_arc_for_character(character_id: UUID, request: AdvanceArcRequest) -> Dict[str, Any]:
    payload = dict(request.character_arc_state)
    payload["character_id"] = str(character_id)
    return engine.advance_arc(
        character_arc_state=payload,
        scene_analysis=request.scene_analysis,
    )


@router.get("/{character_id}", response_model=List[ArcProgressRead])
def list_character_arcs(character_id: UUID, db: Session = Depends(get_db)) -> List[ArcProgressRead]:
    return ArcService(db).list_for_character(character_id)


@router.post("/recompute")
def recompute_arcs(request: RecomputeArcRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    service = ArcService(db)
    if request.episode_id is not None:
        updated = service.recompute_for_episode(project_id=request.project_id, episode_id=request.episode_id)
    else:
        updated = service.recompute_for_project(project_id=request.project_id)
    db.commit()
    return {
        "project_id": str(request.project_id),
        "episode_id": str(request.episode_id) if request.episode_id else None,
        "updated": updated,
        "status": "accepted" if request.force_recompute else "completed",
    }
