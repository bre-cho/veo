from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from app.core.runtime_paths import render_paths
from app.render.assembly.subtitles.visual_aware_karaoke_writer import (
    write_visual_aware_karaoke_ass,
)
from app.render.manifest.manifest_service import ManifestService


class SubtitleRebuildService:
    """Regenerates the episode-level ASS subtitle file after a timeline drift.

    After scene durations change and offsets are rebuilt, this service
    reads the updated ``global_word_timings`` from every scene manifest and
    writes a fresh ``{episode_id}.ass`` file under
    ``{subtitles_dir}/{project_id}/``.
    """

    def __init__(self) -> None:
        self.manifest = ManifestService()

    def rebuild_episode_subtitles(
        self,
        project_id: str,
        episode_id: str,
    ) -> dict:
        """Regenerate the episode subtitle file from current global word timings.

        Args:
            project_id: Owning project identifier.
            episode_id: Episode to rebuild subtitles for.

        Returns:
            Dict with ``status``, ``subtitle_path``, ``scene_count``, and
            ``word_track_count``.
        """
        manifests = self.manifest.list_episode(project_id, episode_id)
        manifests.sort(key=lambda x: x["scene_id"])

        word_tracks: List[Dict[str, Any]] = []
        scene_placements: Dict[str, Dict[str, Any]] = {}

        for item in manifests:
            scene_id = item["scene_id"]

            global_words: List[Dict[str, Any]] = item.get("global_word_timings") or []

            if not global_words:
                global_words = self._build_global_words(item)

            if global_words:
                word_tracks.append({
                    "scene_id": scene_id,
                    "words": global_words,
                })

            scene_placements[scene_id] = item.get("subtitle_placement") or {
                "style_name": "Bottom",
                "placement": "bottom",
            }

        out_dir = Path(render_paths.subtitles_dir) / project_id
        out_dir.mkdir(parents=True, exist_ok=True)

        subtitle_path = str(out_dir / f"{episode_id}.ass")

        write_visual_aware_karaoke_ass(
            word_tracks=word_tracks,
            scene_placements=scene_placements,
            output_path=subtitle_path,
        )

        for item in manifests:
            self.manifest.patch_scene(
                project_id,
                episode_id,
                item["scene_id"],
                {
                    "subtitle_path": subtitle_path,
                    "subtitle_rebuilt_after_drift": True,
                },
            )

        return {
            "status": "subtitle_rebuilt",
            "subtitle_path": subtitle_path,
            "scene_count": len(manifests),
            "word_track_count": len(word_tracks),
        }

    def _build_global_words(self, manifest: dict) -> List[Dict[str, Any]]:
        """Fallback: derive global word timings from scene-local timings + offset."""
        timeline = manifest.get("timeline") or {}
        offset = float(timeline.get("start_sec") or 0)

        rebuilt: List[Dict[str, Any]] = []

        for word in manifest.get("word_timings") or []:
            rebuilt.append({
                "word": word["word"],
                "start_sec": round(offset + float(word["start_sec"]), 3),
                "end_sec": round(offset + float(word["end_sec"]), 3),
            })

        return rebuilt
