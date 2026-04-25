from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


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
        order_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Replace (or insert) the chunk entry for *scene_id* and persist.

        Chunks are kept in ``order_index`` order when that field is available,
        otherwise they fall back to ``scene_id`` lexicographic order so the
        concat step always processes scenes in the correct sequence.

        Args:
            project_id: Owning project identifier.
            episode_id: Episode identifier.
            scene_id: Scene whose chunk is being updated.
            chunk_path: Absolute path to the encoded MP4 chunk.
            duration_sec: Duration of the chunk in seconds.
            order_index: Optional integer position of the scene within the
                episode.  When provided, chunks are sorted by this value so
                numeric ordering (1, 2, 10) is respected instead of
                lexicographic ordering (1, 10, 2).

        Returns:
            The full updated index dict.
        """
        index = self.load(project_id, episode_id)

        # Remove any existing entry for this scene.
        chunks = [c for c in index.get("chunks", []) if c["scene_id"] != scene_id]
        entry: Dict[str, Any] = {
            "scene_id": scene_id,
            "chunk_path": chunk_path,
            "duration_sec": duration_sec,
        }
        if order_index is not None:
            entry["order_index"] = order_index
        chunks.append(entry)
        chunks.sort(
            key=lambda c: (
                int(c.get("order_index", 999999)),
                c.get("scene_id", ""),
            )
        )

        index["chunks"] = chunks
        index["total_duration_sec"] = round(
            sum(float(c.get("duration_sec") or 0) for c in chunks),
            3,
        )
        self.save(project_id, episode_id, index)
        return index
