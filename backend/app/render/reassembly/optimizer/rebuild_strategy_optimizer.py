from __future__ import annotations

from app.render.reassembly._sort_utils import scene_sort_key
from app.render.reassembly.optimizer.rebuild_cost_estimator import RebuildCostEstimator


class RebuildStrategyOptimizer:
    """Choose the cheapest safe rebuild strategy for a smart reassembly.

    Four candidate strategies are evaluated:

    * ``changed_only``  — rebuild only the changed scene.
    * ``dependency_set`` — rebuild all required (and optionally optional) scenes.
    * ``affected_range`` — rebuild the changed scene and all following scenes
      (required for global-burn-in subtitle drift).
    * ``full_rebuild`` — rebuild every scene (always safe fallback).

    The optimizer picks the safe candidate with the lowest estimated cost.
    Safety rules:

    * ``changed_only`` is only safe when there is no timeline drift *and* the
      required set is a subset of the changed-scene-only set.
    * ``dependency_set`` is safe when required scenes are fully covered and
      there is no timeline drift mandating a range rebuild.
    * ``affected_range`` is safe when timeline drift is present or an
      affected-range is provided.
    * ``full_rebuild`` is always safe.
    * When ``force_full_rebuild=True`` the full-rebuild strategy is always chosen.
    * If no safe candidate can be found (edge case), full_rebuild is used.
    """

    def __init__(self) -> None:
        self._cost = RebuildCostEstimator()

    def choose_strategy(
        self,
        all_manifests: list,
        changed_scene_id: str,
        required_scene_ids: list,
        optional_scene_ids: list,
        affected_range_scene_ids: list,
        change_type: str,
        has_timeline_drift: bool,
        force_full_rebuild: bool = False,
        include_optional: bool = False,
    ) -> dict:
        """Evaluate all candidate strategies and return the optimal choice.

        Args:
            all_manifests: Full list of scene manifest dicts for the episode.
            changed_scene_id: The scene whose content changed.
            required_scene_ids: Scenes classified as required by the policy.
            optional_scene_ids: Scenes classified as optional by the policy.
            affected_range_scene_ids: Scenes in the affected timeline range.
            change_type: Category of the change.
            has_timeline_drift: Whether the changed scene has a duration drift.
            force_full_rebuild: Override — always choose ``full_rebuild``.
            include_optional: Whether optional scenes should be included in
                the ``dependency_set`` candidate.

        Returns:
            Dict with ``chosen_strategy`` (the selected candidate dict) and
            ``candidates`` (all evaluated candidate dicts).
        """
        manifests_by_id: dict = {item["scene_id"]: item for item in all_manifests}

        def _sorted_ids(ids: list) -> list:
            return sorted(
                [sid for sid in ids if sid in manifests_by_id],
                key=lambda sid: scene_sort_key(manifests_by_id[sid]),
            )

        changed_only = [changed_scene_id]

        dependency_set = _sorted_ids(
            list(
                set(required_scene_ids) | (set(optional_scene_ids) if include_optional else set())
            )
        )

        affected_range = _sorted_ids(list(set(affected_range_scene_ids)))

        full = _sorted_ids(list(manifests_by_id.keys()))

        required_set = set(required_scene_ids)

        candidates = [
            self._estimate_strategy(
                strategy="changed_only",
                scene_ids=changed_only,
                manifests_by_id=manifests_by_id,
                change_type=change_type,
                safe=(
                    not has_timeline_drift
                    and required_set.issubset(set(changed_only))
                ),
                reason="only changed scene is rebuilt",
            ),
            self._estimate_strategy(
                strategy="dependency_set",
                scene_ids=dependency_set,
                manifests_by_id=manifests_by_id,
                change_type=change_type,
                safe=(
                    required_set.issubset(set(dependency_set))
                    and not has_timeline_drift
                ),
                reason="rebuilds all required dependency scenes",
            ),
            self._estimate_strategy(
                strategy="affected_range",
                scene_ids=affected_range,
                manifests_by_id=manifests_by_id,
                change_type=change_type,
                safe=has_timeline_drift or bool(affected_range),
                reason="rebuilds affected timeline range",
            ),
            self._estimate_strategy(
                strategy="full_rebuild",
                scene_ids=full,
                manifests_by_id=manifests_by_id,
                change_type=change_type,
                safe=True,
                reason="safest fallback rebuilds all scenes",
            ),
        ]

        if force_full_rebuild:
            chosen = candidates[-1]
        else:
            safe_candidates = [c for c in candidates if c["safe"] and c["scene_ids"]]
            if not safe_candidates:
                chosen = candidates[-1]  # full_rebuild always safe
            else:
                chosen = min(
                    safe_candidates,
                    key=lambda x: (x["estimated_cost"], x["estimated_time_sec"]),
                )

        return {
            "chosen_strategy": chosen,
            "candidates": candidates,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _estimate_strategy(
        self,
        strategy: str,
        scene_ids: list,
        manifests_by_id: dict,
        change_type: str,
        safe: bool,
        reason: str,
    ) -> dict:
        manifests = [manifests_by_id[sid] for sid in scene_ids if sid in manifests_by_id]
        estimate = self._cost.estimate_many(manifests, change_type)
        return {
            "strategy": strategy,
            "scene_ids": scene_ids,
            "estimated_cost": estimate["estimated_cost"],
            "estimated_time_sec": estimate["estimated_time_sec"],
            "safe": safe,
            "reason": reason,
            "details": estimate,
        }
