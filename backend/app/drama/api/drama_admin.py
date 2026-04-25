from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.drama.services.scene_recompute_service import SceneRecomputeService
from app.drama.workers.drama_scene_worker import process_scene

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


class ProcessSceneRequest(BaseModel):
    project_id: UUID
    character_ids: Optional[List[UUID]] = None
    scene_context: Optional[Dict[str, Any]] = None
    async_mode: bool = False


@router.post("/scenes/{scene_id}/process", status_code=status.HTTP_200_OK)
def process_scene_endpoint(
    scene_id: UUID,
    payload: ProcessSceneRequest,
    response: Response,
) -> Dict[str, Any]:
    """Trigger the full drama processing pipeline for a single scene.

    When async_mode is True the task is dispatched to the Celery queue and the
    endpoint returns 202 immediately.  When async_mode is False (default) the
    task runs synchronously in-process and returns 200.
    """
    ctx: Dict[str, Any] = {
        "scene_id": str(scene_id),
        "project_id": str(payload.project_id),
        **(payload.scene_context or {}),
    }
    if payload.character_ids is not None:
        ctx["character_ids"] = [str(cid) for cid in payload.character_ids]

    if payload.async_mode:
        task = process_scene.delay(str(scene_id), ctx)
        response.status_code = status.HTTP_202_ACCEPTED
        return {"queued": True, "task_id": task.id, "scene_id": str(scene_id)}

    result = process_scene(str(scene_id), ctx)
    return {"queued": False, **result}
