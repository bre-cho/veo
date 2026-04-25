from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class ChunkIndex:
    """Persists and manages the per-episode chunk manifest.

    The index is stored as a JSON file at
    ``{base_dir}/{project_id}/{episode_id}/chunk_index.json``.
    Each entry in ``chunks`` carries ``scene_id``, ``chunk_path``, and
    ``duration_sec``.
    """

    def __init__(self, base_dir: str = "/data/renders/chunks") -> None:
        self.base_dir = Path(base_dir)

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    def index_path(self, project_id: str, episode_id: str) -> Path:
        return self.base_dir / project_id / episode_id / "chunk_index.json"

    # ------------------------------------------------------------------
    # Load / save
    # ------------------------------------------------------------------

    def load(self, project_id: str, episode_id: str) -> Dict[str, Any]:
        """Return the index or an empty skeleton if none exists yet."""
        path = self.index_path(project_id, episode_id)
        if not path.exists():
            return {"project_id": project_id, "episode_id": episode_id, "chunks": []}
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def save(self, project_id: str, episode_id: str, index: Dict[str, Any]) -> str:
        """Persist *index* and return the absolute path of the written file."""
        path = self.index_path(project_id, episode_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(index, fh, ensure_ascii=False, indent=2)
        return str(path)

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def update_chunk(
        self,
        project_id: str,
        episode_id: str,
        scene_id: str,
        chunk_path: str,
        duration_sec: float,
    ) -> Dict[str, Any]:
        """Replace (or insert) the chunk entry for *scene_id* and persist.

        Chunks are kept sorted by ``scene_id`` so that the concat order is
        deterministic.  Returns the full updated index.
        """
        index = self.load(project_id, episode_id)

        # Remove any existing entry for this scene.
        chunks = [c for c in index.get("chunks", []) if c["scene_id"] != scene_id]
        chunks.append({"scene_id": scene_id, "chunk_path": chunk_path, "duration_sec": duration_sec})
        chunks.sort(key=lambda c: c["scene_id"])

        index["chunks"] = chunks
        index["total_duration_sec"] = round(
            sum(float(c.get("duration_sec") or 0) for c in chunks),
            3,
        )
        self.save(project_id, episode_id, index)
        return index
