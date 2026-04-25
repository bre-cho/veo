from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel

DependencyType = Literal[
    "voice",
    "subtitle",
    "avatar",
    "style",
    "continuity",
    "shared_asset",
    "timeline",
]


class SceneDependency(BaseModel):
    """A directed dependency edge from one scene to another.

    Attributes:
        source_scene_id: The scene that *causes* a rebuild.
        target_scene_id: The scene that *needs to be rebuilt* when the source
            changes.
        dependency_type: Category of the dependency.
        reason: Human-readable explanation of why the dependency exists.
        strength: Relative importance of the dependency (0 – 1).
    """

    source_scene_id: str
    target_scene_id: str
    dependency_type: DependencyType
    reason: str
    strength: float = 1.0


class SceneDependencyGraph(BaseModel):
    """Full dependency graph for one episode.

    Attributes:
        project_id: Owning project.
        episode_id: Episode this graph describes.
        dependencies: All directed dependency edges in the episode.
        scene_metadata: Light metadata snapshot per scene used when rebuilding
            the graph (e.g. ``order_index``, ``avatar_id``, ``style_id``).
    """

    project_id: str
    episode_id: str
    dependencies: List[SceneDependency]
    scene_metadata: Dict[str, Dict] = {}
