from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from app.render.assembly.subtitles.visual_aware_karaoke_writer import (
    write_visual_aware_karaoke_ass,
)
from app.render.manifest.manifest_service import ManifestService


class PerSceneSubtitleService:
    """Generates a per-scene ``.ass`` subtitle file for a single scene.

    Unlike :class:`~app.render.reassembly.subtitle_rebuild_service.SubtitleRebuildService`,
    which regenerates the *episode-level* subtitle file, this service writes a
    separate ``{scene_id}.ass`` under
    ``/data/renders/subtitles/{project_id}/{episode_id}/``.

    Word timings used are the scene-local ``word_timings`` (falling back to
    ``global_word_timings`` when local timings are absent).
    """

    def __init__(self, manifest_base_dir: str = "/data/renders/manifests") -> None:
        self.manifest = ManifestService(base_dir=manifest_base_dir)

    def rebuild_scene_subtitle(
        self,
        project_id: str,
        episode_id: str,
        scene_id: str,
    ) -> Dict[str, Any]:
        """Generate (or regenerate) the per-scene subtitle file.

        Args:
            project_id: Owning project identifier.
            episode_id: Episode that contains the scene.
            scene_id: Scene to generate a subtitle file for.

        Returns:
            Dict with ``status``, ``scene_id``, and ``subtitle_path``.
        """
        item = self.manifest.get_scene(project_id, episode_id, scene_id)

        words: List[Dict[str, Any]] = item.get("word_timings") or []
        if not words:
            words = item.get("global_word_timings") or []

        word_tracks = [{"scene_id": scene_id, "words": words}]

        scene_placements = {
            scene_id: item.get("subtitle_placement") or {
                "style_name": "Bottom",
                "placement": "bottom",
            }
        }

        out_dir = Path(f"/data/renders/subtitles/{project_id}/{episode_id}")
        out_dir.mkdir(parents=True, exist_ok=True)

        subtitle_path = str(out_dir / f"{scene_id}.ass")

        write_visual_aware_karaoke_ass(
            word_tracks=word_tracks,
            scene_placements=scene_placements,
            output_path=subtitle_path,
        )

        self.manifest.patch_scene(
            project_id,
            episode_id,
            scene_id,
            {
                "subtitle_path": subtitle_path,
                "subtitle_burn_in_mode": "per_scene_burn_in",
            },
        )

        return {
            "status": "scene_subtitle_rebuilt",
            "scene_id": scene_id,
            "subtitle_path": subtitle_path,
        }

    def rebuild_episode_per_scene_subtitles(
        self,
        project_id: str,
        episode_id: str,
    ) -> Dict[str, Any]:
        """Generate a per-scene ``.ass`` file for every scene in *episode_id*.

        Calls :meth:`rebuild_scene_subtitle` for each scene manifest returned
        by the manifest service.

        Args:
            project_id: Owning project identifier.
            episode_id: Episode to process.

        Returns:
            Dict with ``status``, ``count``, and ``items`` (list of per-scene
            results from :meth:`rebuild_scene_subtitle`).
        """
        manifests = self.manifest.list_episode(project_id, episode_id)

        results = []
        for item in manifests:
            results.append(
                self.rebuild_scene_subtitle(
                    project_id=project_id,
                    episode_id=episode_id,
                    scene_id=item["scene_id"],
                )
            )

        return {
            "status": "per_scene_subtitles_built",
            "count": len(results),
            "items": results,
        }
