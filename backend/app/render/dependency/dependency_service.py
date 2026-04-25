from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from app.core.runtime_paths import render_paths
from app.render.dependency.dependency_graph import DependencyGraph
from app.render.dependency.dependency_resolver import DependencyResolver
from app.render.manifest.manifest_service import ManifestService


class DependencyService:
    """Builds, persists, and queries the per-episode scene dependency graph.

    Graph files are stored under
    ``{base_dir}/{project_id}/{episode_id}.json`` (default base dir is
    ``render_paths.dependency_dir``).

    Typical usage::

        svc = DependencyService()
        # Build & persist the graph after initial assembly:
        svc.build_graph(project_id, episode_id)

        # Query which scenes need rebuilding when scene_003 voice changes:
        affected = svc.affected_scenes(project_id, episode_id, "scene_003", "voice")
    """

    def __init__(
        self,
        manifest_base_dir: str | None = None,
        dependency_base_dir: str | None = None,
    ) -> None:
        self.manifest = ManifestService(base_dir=manifest_base_dir)
        self.resolver = DependencyResolver()
        self._base_dir = Path(dependency_base_dir if dependency_base_dir is not None else render_paths.dependency_dir)

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    def graph_path(self, project_id: str, episode_id: str) -> Path:
        return self._base_dir / project_id / f"{episode_id}.json"

    # ------------------------------------------------------------------
    # Build / load
    # ------------------------------------------------------------------

    def build_graph(self, project_id: str, episode_id: str) -> Dict[str, Any]:
        """Build the dependency graph from current manifests and persist it.

        Args:
            project_id: Owning project.
            episode_id: Episode to analyse.

        Returns:
            The full graph dict.
        """
        manifests = self.manifest.list_episode(project_id, episode_id)

        dependencies = self.resolver.build_from_manifests(manifests)

        graph: Dict[str, Any] = {
            "project_id": project_id,
            "episode_id": episode_id,
            "dependencies": dependencies,
            "scene_metadata": {
                item["scene_id"]: {
                    "order_index": item.get("order_index"),
                    "avatar_id": item.get("avatar_id"),
                    "style_id": item.get("style_id"),
                    "shared_assets": item.get("shared_assets", []),
                }
                for item in manifests
            },
        }

        path = self.graph_path(project_id, episode_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as fh:
            json.dump(graph, fh, ensure_ascii=False, indent=2)

        return graph

    def load_graph(self, project_id: str, episode_id: str) -> Dict[str, Any]:
        """Load the persisted graph, building it on-the-fly if missing.

        Args:
            project_id: Owning project.
            episode_id: Episode to load.

        Returns:
            The graph dict (freshly built if not yet persisted).
        """
        path = self.graph_path(project_id, episode_id)
        if not path.exists():
            return self.build_graph(project_id, episode_id)

        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def affected_scenes_with_reasons(
        self,
        project_id: str,
        episode_id: str,
        changed_scene_id: str,
        change_type: str,
    ) -> dict:
        """Return all affected scene IDs mapped to their rebuild reasons.

        Args:
            project_id: Owning project.
            episode_id: Episode that contains the changed scene.
            changed_scene_id: The scene whose content changed.
            change_type: Category of the change.

        Returns:
            Dict mapping scene_id -> list of reason dicts.
        """
        graph_data = self.load_graph(project_id, episode_id)
        graph = DependencyGraph(graph_data["dependencies"])
        return graph.affected_scenes_with_reasons(
            changed_scene_id=changed_scene_id,
            change_type=change_type,
        )

    def affected_scenes(
        self,
        project_id: str,
        episode_id: str,
        changed_scene_id: str,
        change_type: str,
    ) -> List[str]:
        """Return all scene IDs that must be rebuilt given a change.

        Args:
            project_id: Owning project.
            episode_id: Episode that contains the changed scene.
            changed_scene_id: The scene whose content changed.
            change_type: Category of the change — ``"voice"``, ``"subtitle"``,
                ``"avatar"``, ``"style"``, ``"shared_asset"``,
                ``"timeline"``, ``"continuity"``, or ``"all"``.

        Returns:
            List of affected scene IDs (includes *changed_scene_id* itself).
        """
        graph_data = self.load_graph(project_id, episode_id)
        graph = DependencyGraph(graph_data["dependencies"])
        return graph.affected_scenes(
            changed_scene_id=changed_scene_id,
            change_type=change_type,
        )
