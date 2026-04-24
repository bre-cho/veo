from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.drama.services.scene_recompute_service import SceneRecomputeService

router = APIRouter(prefix="/api/v1/drama/admin", tags=["drama-admin"])


@router.post("/episodes/{episode_id}/recompute")
def recompute_episode_state(
    episode_id: UUID,
    starting_scene_id: UUID,
    scene_ids: List[UUID] = Query(...),
    db: Session = Depends(get_db),
):
    service = SceneRecomputeService(db)
    return service.recompute_episode_from_scene(
        episode_id=episode_id,
        starting_scene_id=starting_scene_id,
        ordered_scene_ids=scene_ids,
    )
