from __future__ import annotations

from typing import List


class DependencyGraph:
    """In-memory graph that resolves which scenes are affected by a change.

    The graph is represented as a flat list of dependency dicts (as stored in
    the persisted JSON), each with at minimum:

    * ``source_scene_id`` — the scene that caused the change
    * ``target_scene_id`` — the scene that depends on the source
    * ``dependency_type`` — category of the dependency

    :meth:`affected_scenes` performs a BFS from *changed_scene_id* along edges
    that match *change_type*, returning the set of scenes that must be
    rebuilt.
    """

    def __init__(self, dependencies: list) -> None:
        self.dependencies = dependencies

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def affected_scenes(
        self,
        changed_scene_id: str,
        change_type: str,
        include_self: bool = True,
    ) -> List[str]:
        """Return all scene IDs that are affected by *changed_scene_id*.

        Args:
            changed_scene_id: The scene whose content has changed.
            change_type: Category of the change — one of ``"voice"``,
                ``"subtitle"``, ``"avatar"``, ``"style"``,
                ``"shared_asset"``, ``"timeline"``, ``"continuity"``,
                or ``"all"``.
            include_self: Whether to include *changed_scene_id* itself in the
                result (almost always ``True``).

        Returns:
            List of scene IDs (order not guaranteed).
        """
        affected: set = set()

        if include_self:
            affected.add(changed_scene_id)

        queue = [changed_scene_id]

        while queue:
            current = queue.pop(0)

            for dep in self.dependencies:
                if dep["source_scene_id"] != current:
                    continue

                if not self._matches_change(dep, change_type):
                    continue

                target = dep["target_scene_id"]

                if target not in affected:
                    affected.add(target)
                    queue.append(target)

        return list(affected)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _matches_change(self, dep: dict, change_type: str) -> bool:
        """Return ``True`` when *dep* is relevant for *change_type*."""
        dep_type = dep.get("dependency_type")

        if change_type == "all":
            return True

        if dep_type == change_type:
            return True

        # A voice change may shift word timings → subtitles must be rebuilt.
        if change_type == "voice" and dep_type in ("subtitle", "timeline"):
            return True

        # An avatar change requires continuity/style scenes to be rebuilt.
        if change_type == "avatar" and dep_type in ("continuity", "style"):
            return True

        return False
