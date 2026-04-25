from __future__ import annotations

from typing import List

from app.core.runtime_paths import render_paths
from app.render.manifest.manifest_reader import ManifestReader
from app.render.manifest.manifest_writer import ManifestWriter


class ManifestService:
    """Facade over :class:`ManifestWriter` and :class:`ManifestReader`."""

    def __init__(self, base_dir: str | None = None) -> None:
        resolved = base_dir if base_dir is not None else render_paths.manifests_dir
        self.writer = ManifestWriter(base_dir=resolved)
        self.reader = ManifestReader(base_dir=resolved)

    # ------------------------------------------------------------------
    # Write / patch
    # ------------------------------------------------------------------

    def patch_scene(
        self,
        project_id: str,
        episode_id: str,
        scene_id: str,
        patch: dict,
    ) -> str:
        """Merge *patch* into the scene manifest and persist.

        Returns the path of the written file.
        """
        return self.writer.patch_scene_manifest(
            project_id=project_id,
            episode_id=episode_id,
            scene_id=scene_id,
            patch=patch,
        )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_scene(
        self,
        project_id: str,
        episode_id: str,
        scene_id: str,
    ) -> dict:
        """Return the scene manifest or raise :exc:`FileNotFoundError`."""
        return self.reader.read_scene_manifest(project_id, episode_id, scene_id)

    def list_episode(
        self,
        project_id: str,
        episode_id: str,
    ) -> List[dict]:
        """Return all scene manifests for the given episode."""
        return self.reader.list_episode_manifests(project_id, episode_id)
