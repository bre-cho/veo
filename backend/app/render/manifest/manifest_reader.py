from __future__ import annotations

import json
from pathlib import Path
from typing import List


class ManifestReader:
    """Reads per-scene JSON manifests from ``base_dir``."""

    def __init__(self, base_dir: str = "/data/renders/manifests") -> None:
        self.base_dir = Path(base_dir)

    def read_scene_manifest(
        self,
        project_id: str,
        episode_id: str,
        scene_id: str,
    ) -> dict:
        """Return the manifest for *scene_id* or raise :exc:`FileNotFoundError`."""
        path = self.base_dir / project_id / episode_id / f"{scene_id}.json"
        if not path.exists():
            raise FileNotFoundError(str(path))
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def list_episode_manifests(
        self,
        project_id: str,
        episode_id: str,
    ) -> List[dict]:
        """Return all scene manifests for *episode_id*, sorted by scene file name."""
        folder = self.base_dir / project_id / episode_id
        if not folder.exists():
            return []
        manifests: List[dict] = []
        for path in sorted(folder.glob("*.json")):
            with open(path, "r", encoding="utf-8") as fh:
                manifests.append(json.load(fh))
        return manifests
