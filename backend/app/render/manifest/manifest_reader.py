from __future__ import annotations

import json
from pathlib import Path
from typing import List

from app.render.reassembly._sort_utils import scene_sort_key


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
        """Return all scene manifests for *episode_id*, ordered by ``order_index``.

        When ``order_index`` (or its alias ``scene_index``) is present in the
        manifest it is used as the primary sort key so numeric ordering is
        respected (scene_1 < scene_2 < scene_10).  Manifests that carry no
        index field fall back to ``scene_id`` lexicographic ordering, which
        preserves the original behaviour for episodes that pre-date the index
        field.
        """
        folder = self.base_dir / project_id / episode_id
        if not folder.exists():
            return []
        items: List[dict] = []
        for path in folder.glob("*.json"):
            with open(path, "r", encoding="utf-8") as fh:
                items.append(json.load(fh))
        items.sort(key=scene_sort_key)
        return items
