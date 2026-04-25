from __future__ import annotations

from typing import Any, Dict, List

from app.render.manifest.manifest_service import ManifestService


def rebuild_global_word_timings(item: dict, offset: float) -> List[Dict[str, Any]]:
    """Recompute word timings for *item* using the episode-level *offset*.

    Args:
        item: Scene manifest dict containing ``word_timings`` (scene-local).
        offset: Start time of this scene within the episode (seconds).

    Returns:
        List of word-timing dicts with global ``start_sec`` / ``end_sec``.
    """
    rebuilt: List[Dict[str, Any]] = []

    for word in item.get("word_timings", []):
        rebuilt.append({
            "word": word["word"],
            "start_sec": round(offset + float(word["start_sec"]), 3),
            "end_sec": round(offset + float(word["end_sec"]), 3),
        })

    return rebuilt


class TimelineRebuilder:
    """Rebuilds timeline offsets for all scenes in an episode.

    After a rerender changes a scene's duration, all subsequent scenes need
    their ``timeline`` (start/end offsets) and ``global_word_timings``
    recalculated from scratch.
    """

    def __init__(self) -> None:
        self.manifest = ManifestService()

    def rebuild_episode_offsets(
        self,
        project_id: str,
        episode_id: str,
    ) -> dict:
        """Recalculate timeline offsets for every scene in the episode.

        Scenes are sorted by ``scene_id``, traversed in order, and each
        scene's manifest is patched with a fresh ``timeline`` dict and
        updated ``global_word_timings``.

        Args:
            project_id: Owning project identifier.
            episode_id: Episode to rebuild.

        Returns:
            Dict with ``project_id``, ``episode_id``,
            ``total_duration_sec``, and ``timeline`` (list of per-scene
            offset summaries).
        """
        manifests = self.manifest.list_episode(project_id, episode_id)
        manifests.sort(key=lambda x: x["scene_id"])

        cursor = 0.0
        rebuilt = []

        for item in manifests:
            duration = float(item.get("duration_sec") or 0)

            timeline = {
                "start_sec": round(cursor, 3),
                "end_sec": round(cursor + duration, 3),
                "duration_sec": duration,
            }

            global_word_timings = rebuild_global_word_timings(item, cursor)

            self.manifest.patch_scene(
                project_id,
                episode_id,
                item["scene_id"],
                {
                    "timeline": timeline,
                    "global_word_timings": global_word_timings,
                },
            )

            rebuilt.append({
                "scene_id": item["scene_id"],
                **timeline,
            })

            cursor += duration

        return {
            "project_id": project_id,
            "episode_id": episode_id,
            "total_duration_sec": round(cursor, 3),
            "timeline": rebuilt,
        }
