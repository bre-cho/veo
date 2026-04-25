from __future__ import annotations

from app.render.reassembly.policy.rebuild_policy_config import REBUILD_POLICY


class RebuildPolicyEngine:
    """Classifies rebuild necessity for each scene based on dependency reasons.

    Decisions:
        * ``required`` — scene must be rebuilt.
        * ``optional`` — scene can be rebuilt when ``force_quality=True``
          or ``include_optional_rebuilds=True``.
        * ``skip`` — dependency strength is below threshold; no rebuild needed.
    """

    def classify_scene(
        self,
        scene_id: str,
        reasons: list,
        force_quality: bool = False,
    ) -> dict:
        """Classify a single scene's rebuild necessity.

        Args:
            scene_id: Scene to classify.
            reasons: List of reason dicts from
                :meth:`~DependencyGraph.affected_scenes_with_reasons`.
            force_quality: When ``True``, optional dependencies are promoted
                to ``required``.

        Returns:
            Dict with keys ``scene_id``, ``decision``, ``max_strength``,
            ``reason``, and (when applicable) ``reasons``.
        """
        if not reasons:
            return {
                "scene_id": scene_id,
                "decision": "skip",
                "max_strength": 0,
                "reason": "no rebuild reason",
            }

        max_strength = max(float(r.get("strength", 0)) for r in reasons)
        dependency_types = {r.get("dependency_type") for r in reasons}

        if dependency_types.intersection(REBUILD_POLICY["always_required"]):
            return {
                "scene_id": scene_id,
                "decision": "required",
                "max_strength": max_strength,
                "reason": "contains always-required dependency",
                "reasons": reasons,
            }

        if max_strength >= REBUILD_POLICY["required_threshold"]:
            return {
                "scene_id": scene_id,
                "decision": "required",
                "max_strength": max_strength,
                "reason": "strength above required threshold",
                "reasons": reasons,
            }

        if max_strength >= REBUILD_POLICY["optional_threshold"]:
            decision = "required" if force_quality else "optional"
            return {
                "scene_id": scene_id,
                "decision": decision,
                "max_strength": max_strength,
                "reason": "quality-sensitive optional dependency",
                "reasons": reasons,
            }

        return {
            "scene_id": scene_id,
            "decision": "skip",
            "max_strength": max_strength,
            "reason": "dependency strength below threshold",
            "reasons": reasons,
        }

    def classify_many(
        self,
        reason_report: dict,
        force_quality: bool = False,
    ) -> dict:
        """Classify all scenes in a reason report.

        Args:
            reason_report: Mapping of scene_id -> list[reason dict].
            force_quality: Passed to :meth:`classify_scene`.

        Returns:
            Mapping of scene_id -> classification dict.
        """
        decisions = {}
        for scene_id, reasons in reason_report.items():
            decisions[scene_id] = self.classify_scene(
                scene_id=scene_id,
                reasons=reasons,
                force_quality=force_quality,
            )
        return decisions

    def required_scene_ids(self, decisions: dict) -> list:
        """Return scene IDs whose decision is ``required``."""
        return [
            scene_id
            for scene_id, result in decisions.items()
            if result["decision"] == "required"
        ]

    def optional_scene_ids(self, decisions: dict) -> list:
        """Return scene IDs whose decision is ``optional``."""
        return [
            scene_id
            for scene_id, result in decisions.items()
            if result["decision"] == "optional"
        ]

    def skipped_scene_ids(self, decisions: dict) -> list:
        """Return scene IDs whose decision is ``skip``."""
        return [
            scene_id
            for scene_id, result in decisions.items()
            if result["decision"] == "skip"
        ]
