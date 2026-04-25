from __future__ import annotations

from typing import Any, Dict

from app.render.manifest.manifest_service import ManifestService
from app.render.reassembly._sort_utils import scene_sort_key
from app.render.reassembly.chunk_builder import ChunkBuilder
from app.render.reassembly.chunk_index import ChunkIndex
from app.render.reassembly.per_scene_subtitle_service import PerSceneSubtitleService


class ChunkBootstrapper:
    """Builds scene chunks for every scene in an episode after a full assembly.

    After the first successful FFmpeg full-assembly pass, this bootstrapper:

    1. Generates a per-scene ``.ass`` subtitle file for every scene (using the
       default ``per_scene_burn_in`` mode so each chunk can be rebuilt
       independently on rerender).
    2. Reads all scene manifests for the episode.
    3. Encodes each scene into a standalone MP4 chunk.
    4. Persists ``chunk_path`` and ``smart_reassembly_ready=True`` in each
       scene's manifest.
    5. Writes a ``chunk_index.json`` for the episode, ordered by
       ``order_index`` (falling back to ``scene_id``).

    Once bootstrapped, :class:`SmartReassemblyService` can rebuild just the
    changed chunk without a ``force_full_rebuild``.
    """

    def __init__(
        self,
        manifest_base_dir: str | None = None,
        chunk_base_dir: str | None = None,
    ) -> None:
        self._manifest = ManifestService(base_dir=manifest_base_dir)
        self._chunk_builder = ChunkBuilder()
        self._chunk_index = ChunkIndex(base_dir=chunk_base_dir)
        self._per_scene_subtitles = PerSceneSubtitleService(manifest_base_dir=manifest_base_dir)

    def bootstrap_episode(self, project_id: str, episode_id: str) -> Dict[str, Any]:
        """Build chunks for every scene in *episode_id* and write the index.

        Args:
            project_id: Owning project.
            episode_id: Episode to bootstrap.

        Returns:
            A result dict with ``status``, ``chunk_count``,
            ``chunk_index_path``, ``chunks``, and ``subtitle_report``.

        Raises:
            ValueError: If no scene manifests are found, or if a scene is
                missing its ``video_path`` or ``audio_path``.
        """
        manifests = self._manifest.list_episode(project_id, episode_id)

        if not manifests:
            raise ValueError(
                f"No scene manifests found for project '{project_id}' episode '{episode_id}'"
            )

        # Generate per-scene subtitle files before encoding so every chunk
        # gets the correct subtitle_path burned in.
        subtitle_report = self._per_scene_subtitles.rebuild_episode_per_scene_subtitles(
            project_id=project_id,
            episode_id=episode_id,
        )

        # Re-read manifests so chunks pick up the freshly written subtitle_path.
        manifests = self._manifest.list_episode(project_id, episode_id)
        manifests.sort(key=scene_sort_key)

        chunks = []
        for scene_manifest in manifests:
            sid = scene_manifest.get("scene_id", "?")
            if not scene_manifest.get("video_path"):
                raise ValueError(f"Missing video_path in manifest for scene '{sid}'")
            if not scene_manifest.get("audio_path"):
                raise ValueError(f"Missing audio_path in manifest for scene '{sid}'")

            chunk = self._chunk_builder.build_scene_chunk(
                project_id=project_id,
                episode_id=episode_id,
                scene_manifest=scene_manifest,
            )
            chunks.append(chunk)

            self._manifest.patch_scene(
                project_id,
                episode_id,
                scene_manifest["scene_id"],
                {
                    "chunk_path": chunk["chunk_path"],
                    "smart_reassembly_ready": True,
                },
            )

        chunks.sort(key=scene_sort_key)

        index: Dict[str, Any] = {
            "project_id": project_id,
            "episode_id": episode_id,
            "smart_reassembly_ready": True,
            "chunks": chunks,
        }
        index_path = self._chunk_index.save(project_id, episode_id, index)

        return {
            "status": "bootstrapped",
            "project_id": project_id,
            "episode_id": episode_id,
            "chunk_count": len(chunks),
            "chunk_index_path": index_path,
            "chunks": chunks,
            "subtitle_report": subtitle_report,
        }

