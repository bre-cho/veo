from __future__ import annotations

from typing import Any, Dict, List


class RebuildPolicyEngine:
    """Classify rebuild necessity for individual scenes.

    Uses ``dependency_type`` and ``strength`` from the reason report produced
    by :meth:`~DependencyGraph.affected_scenes_with_reasons` to determine
    whether a scene *must* be rebuilt, *may* be rebuilt, or can be skipped.

    Decisions:
        * ``mandatory`` — scene must be rebuilt (self/timeline type, or
          strength ≥ 0.85).
        * ``optional`` — scene can be rebuilt for quality (strength ≥ 0.50).
        * ``skip`` — dependency strength is below threshold; no rebuild needed.
    """

    MANDATORY_TYPES = {"self", "timeline"}
    MANDATORY_STRENGTH = 0.85
    OPTIONAL_STRENGTH = 0.50

    def classify_scene(
        self,
        reasons: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Classify a single scene's rebuild necessity.

        Args:
            reasons: List of reason dicts (each with at least
                ``dependency_type`` and ``strength`` keys).

        Returns:
            Dict with ``policy``, ``max_strength``, ``reason_count``,
            and ``reason_types``.
        """
        max_strength = max(
            (float(r.get("strength", 0.0) or 0.0) for r in reasons),
            default=0.0,
        )
        reason_types = {r.get("dependency_type") for r in reasons}

        if reason_types.intersection(self.MANDATORY_TYPES):
            policy = "mandatory"
        elif max_strength >= self.MANDATORY_STRENGTH:
            policy = "mandatory"
        elif max_strength >= self.OPTIONAL_STRENGTH:
            policy = "optional"
        else:
            policy = "skip"

        return {
            "policy": policy,
            "max_strength": max_strength,
            "reason_count": len(reasons),
            "reason_types": sorted(t for t in reason_types if t),
        }

    def classify_all(
        self,
        rebuild_reasons: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Dict[str, Any]]:
        """Classify all scenes in a reason report.

        Args:
            rebuild_reasons: Mapping of scene_id -> list[reason dict].

        Returns:
            Mapping of scene_id -> classification dict.
        """
        return {
            scene_id: self.classify_scene(reasons)
            for scene_id, reasons in rebuild_reasons.items()
        }

    def mandatory_scene_ids(
        self,
        policy_report: Dict[str, Dict[str, Any]],
    ) -> List[str]:
        """Return scene IDs whose policy is ``mandatory``."""
        return [
            scene_id
            for scene_id, report in policy_report.items()
            if report.get("policy") == "mandatory"
        ]

    def optional_scene_ids(
        self,
        policy_report: Dict[str, Dict[str, Any]],
    ) -> List[str]:
        """Return scene IDs whose policy is ``optional``."""
        return [
            scene_id
            for scene_id, report in policy_report.items()
            if report.get("policy") == "optional"
        ]

    def skipped_scene_ids(
        self,
        policy_report: Dict[str, Dict[str, Any]],
    ) -> List[str]:
        """Return scene IDs whose policy is ``skip``."""
        return [
            scene_id
            for scene_id, report in policy_report.items()
            if report.get("policy") == "skip"
        ]
