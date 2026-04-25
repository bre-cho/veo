from __future__ import annotations

from typing import Any, Dict, List

from app.render.manifest.manifest_service import ManifestService


class AffectedRangeResolver:
    """Determines which scene manifests must be rebuilt after a rerender.

    When there is **no** timeline drift, only the changed scene needs a new
    chunk.  When drift is detected, the changed scene **and every scene that
    comes after it** must be rebuilt because the burnt-in subtitle timestamps
    for those scenes have shifted.

    Scenes are sorted lexicographically by ``scene_id`` — the same order used
    by :class:`~app.render.reassembly.timeline_rebuilder.TimelineRebuilder`.
    """

    def __init__(self, manifest_base_dir: str = "/data/renders/manifests") -> None:
        self.manifest = ManifestService(base_dir=manifest_base_dir)

    def resolve(
        self,
        project_id: str,
        episode_id: str,
        changed_scene_id: str,
        has_timeline_drift: bool,
    ) -> List[Dict[str, Any]]:
        """Return the ordered list of scene manifests that need chunk rebuilds.

        Args:
            project_id: Owning project identifier.
            episode_id: Episode to query.
            changed_scene_id: The scene whose duration (and chunk) changed.
            has_timeline_drift: When ``True``, return the changed scene plus
                all scenes that follow it.  When ``False``, return only the
                changed scene.

        Returns:
            List of scene manifest dicts sorted by ``scene_id``.

        Raises:
            ValueError: If *changed_scene_id* is not found in the episode.
        """
        manifests = self.manifest.list_episode(project_id, episode_id)
        manifests.sort(key=lambda x: x["scene_id"])

        if not has_timeline_drift:
            return [item for item in manifests if item["scene_id"] == changed_scene_id]

        changed_index: int | None = None

        for idx, item in enumerate(manifests):
            if item["scene_id"] == changed_scene_id:
                changed_index = idx
                break

        if changed_index is None:
            raise ValueError(
                f"Scene not found in episode '{episode_id}': '{changed_scene_id}'"
            )

        return manifests[changed_index:]
