from __future__ import annotations

from pydantic import BaseModel


class SmartReassemblyRequest(BaseModel):
    """Request to smart-reassemble an episode after one scene has been rerendered.

    Attributes:
        project_id: Owning project.
        episode_id: Episode that contains the changed scene.
        changed_scene_id: The scene whose chunk must be rebuilt.
        force_full_rebuild: When ``True``, rebuild *all* scene chunks regardless
            of whether a chunk index already exists.
    """

    project_id: str
    episode_id: str
    changed_scene_id: str
    force_full_rebuild: bool = False
