from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.drama.schemas.drama_state import DramaSceneStateRead
from app.drama.services.state_query_service import StateQueryService

router = APIRouter(prefix="/api/v1/drama/state", tags=["drama-state"])


@router.get("/scenes/{scene_id}", response_model=DramaSceneStateRead)
def get_scene_state(scene_id: UUID, db: Session = Depends(get_db)):
    service = StateQueryService(db)
    state = service.get_scene_state(scene_id)
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drama scene state not found")
    return state


@router.get("/episodes/{episode_id}/latest")
def get_latest_episode_state(
    episode_id: UUID,
    project_id: Optional[UUID] = Query(default=None),
    db: Session = Depends(get_db),
):
    service = StateQueryService(db)
    result = service.get_latest_episode_state(episode_id=episode_id, project_id=project_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No scene state found for episode")
    return result


@router.get("/projects/{project_id}/dashboard")
def get_project_state_dashboard(project_id: UUID, db: Session = Depends(get_db)):
    service = StateQueryService(db)
    return service.get_project_dashboard(project_id)
