from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.render.manifest.manifest_service import ManifestService

router = APIRouter(prefix="/api/v1/render/manifest", tags=["render-manifest"])

_service = ManifestService()


@router.get("/{project_id}/{episode_id}", response_model=List[Dict[str, Any]])
def list_episode_manifests(project_id: str, episode_id: str) -> List[Dict[str, Any]]:
    """Return all scene manifests for the given episode."""
    return _service.list_episode(project_id, episode_id)


@router.get("/{project_id}/{episode_id}/{scene_id}", response_model=Dict[str, Any])
def get_scene_manifest(
    project_id: str,
    episode_id: str,
    scene_id: str,
) -> Dict[str, Any]:
    """Return the manifest for a specific scene."""
    try:
        return _service.get_scene(project_id, episode_id, scene_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Manifest not found: {scene_id}")
