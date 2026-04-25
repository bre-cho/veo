from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class ManifestWriter:
    """Writes and patches per-scene JSON manifests to ``base_dir``."""

    def __init__(self, base_dir: str = "/data/renders/manifests") -> None:
        self.base_dir = Path(base_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write_scene_manifest(self, manifest: dict) -> str:
        """Serialise *manifest* to disk and return the absolute path."""
        project_id = manifest["project_id"]
        episode_id = manifest["episode_id"]
        scene_id = manifest["scene_id"]

        out_dir = self.base_dir / project_id / episode_id
        out_dir.mkdir(parents=True, exist_ok=True)

        manifest["updated_at"] = datetime.utcnow().isoformat()

        path = out_dir / f"{scene_id}.json"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, ensure_ascii=False, indent=2)

        return str(path)

    def patch_scene_manifest(
        self,
        project_id: str,
        episode_id: str,
        scene_id: str,
        patch: dict,
    ) -> str:
        """Read the existing manifest, merge *patch* into it, and re-write.

        If no manifest exists yet, a new one is created from *patch*.
        The ``project_id``, ``episode_id``, and ``scene_id`` keys are always
        stamped, regardless of what *patch* contains.
        """
        path = self._path(project_id, episode_id, scene_id)

        existing: dict = {}
        if path.exists():
            with open(path, "r", encoding="utf-8") as fh:
                existing = json.load(fh)

        existing.update(patch)
        existing["project_id"] = project_id
        existing["episode_id"] = episode_id
        existing["scene_id"] = scene_id

        return self.write_scene_manifest(existing)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _path(self, project_id: str, episode_id: str, scene_id: str) -> Path:
        return self.base_dir / project_id / episode_id / f"{scene_id}.json"
