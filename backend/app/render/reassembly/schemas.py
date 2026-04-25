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
        change_type: Category of the change — used by the dependency graph to
            resolve which other scenes (if any) must also be rebuilt.
            Defaults to ``"subtitle"`` so that, unless a voice/avatar/style
            change is explicitly declared, only the changed scene's chunk is
            rebuilt.  Pass ``"voice"`` for a TTS rerender, ``"avatar"`` or
            ``"style"`` for visual rerenders, or ``"all"`` to force a full
            dependency closure rebuild.
    """

    project_id: str
    episode_id: str
    changed_scene_id: str
    force_full_rebuild: bool = False
    change_type: str = "subtitle"
    force_quality_rebuild: bool = False
    include_optional_rebuilds: bool = False
    # Budget control — per-request overrides.  When None the value from the
    # resolved budget_policy preset is used.
    budget_policy: str = "balanced"
    max_rebuild_cost: float | None = None
    max_rebuild_time_sec: float | None = None
    allow_budget_downgrade: bool | None = None
