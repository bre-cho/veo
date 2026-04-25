from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class RerenderSceneRequest(BaseModel):
    """Request to rerender a single scene.

    Attributes:
        project_id: Owning project.
        episode_id: Episode that contains the scene.
        scene_id: Scene to rerender.
        mode: Which component(s) to regenerate — ``"audio"``, ``"video"``,
            or ``"both"`` (default).
        override_voiceover_text: Replace the voiceover stored in the manifest
            before regenerating audio.
        override_duration_sec: Replace the scene duration stored in the
            manifest before regenerating.
        force: If ``True``, skip status guards and always rerender.
    """

    project_id: str
    episode_id: str
    scene_id: str

    mode: Literal["audio", "video", "both"] = "both"

    override_voiceover_text: Optional[str] = None
    override_duration_sec: Optional[float] = None
    force: bool = False
