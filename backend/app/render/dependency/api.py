from __future__ import annotations

from fastapi import APIRouter

from app.render.dependency.dependency_service import DependencyService

router = APIRouter(prefix="/api/v1/render/dependency", tags=["Render Dependency"])

_service = DependencyService()


@router.post("/build/{project_id}/{episode_id}")
def build_dependency_graph(project_id: str, episode_id: str):
    """Build (or rebuild) the dependency graph for an episode.

    Reads the current scene manifests, computes all dependency edges, and
    persists the graph under ``/data/renders/dependency/{project_id}/{episode_id}.json``.
    """
    return _service.build_graph(project_id, episode_id)


@router.get("/affected-with-reasons/{project_id}/{episode_id}/{scene_id}/{change_type}")
def get_affected_scenes_with_reasons(
    project_id: str,
    episode_id: str,
    scene_id: str,
    change_type: str,
):
    """Return all scene IDs and their rebuild reasons when *scene_id* changes."""
    affected = _service.affected_scenes_with_reasons(
        project_id=project_id,
        episode_id=episode_id,
        changed_scene_id=scene_id,
        change_type=change_type,
    )
    return {
        "project_id": project_id,
        "episode_id": episode_id,
        "changed_scene_id": scene_id,
        "change_type": change_type,
        "affected": affected,
    }

def get_affected_scenes(
    project_id: str,
    episode_id: str,
    scene_id: str,
    change_type: str,
):
    """Return all scene IDs that must be rebuilt when *scene_id* changes.

    ``change_type`` must be one of ``voice``, ``subtitle``, ``avatar``,
    ``style``, ``shared_asset``, ``timeline``, ``continuity``, or ``all``.
    """
    return {
        "project_id": project_id,
        "episode_id": episode_id,
        "changed_scene_id": scene_id,
        "change_type": change_type,
        "affected_scenes": _service.affected_scenes(
            project_id=project_id,
            episode_id=episode_id,
            changed_scene_id=scene_id,
            change_type=change_type,
        ),
    }
