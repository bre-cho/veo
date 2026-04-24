from __future__ import annotations

from typing import Any, Dict, List


class ContinuityEngine:
    """Checks and summarizes emotional / relational continuity across scenes."""

    def inspect_transition(
        self,
        previous_scene_state: Dict[str, Any],
        current_scene_context: Dict[str, Any],
        current_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []

        prev_dominant = previous_scene_state.get("dominant_character_id")
        cur_dominant = current_analysis.get("power_shift", {}).get("dominant_character_id")
        if prev_dominant and cur_dominant and prev_dominant != cur_dominant:
            issues.append(
                {
                    "type": "power_transition",
                    "severity": "info",
                    "message": "Dominance changed across scenes; ensure a visible transition beat exists.",
                }
            )

        prev_trust = previous_scene_state.get("trust_snapshot", {})
        cur_rel = current_analysis.get("relationship_snapshot", {})
        if prev_trust and cur_rel and prev_trust != cur_rel.get("trust_snapshot"):
            issues.append(
                {
                    "type": "relationship_shift",
                    "severity": "warning",
                    "message": "Relationship values changed; downstream reactions should reflect the shift.",
                }
            )

        if current_analysis.get("tension_breakdown", {}).get("tension_score", 0) > 80 and not current_scene_context.get(
            "aftermath_beat_present", False
        ):
            issues.append(
                {
                    "type": "missing_aftermath",
                    "severity": "warning",
                    "message": "High-tension scene should be followed by a readable aftermath or carry-over marker.",
                }
            )

        return {
            "scene_id": current_scene_context.get("scene_id"),
            "status": "review" if issues else "ok",
            "issues": issues,
            "continuity_notes": self._notes_from_issues(issues),
        }

    def _notes_from_issues(self, issues: List[Dict[str, Any]]) -> List[str]:
        if not issues:
            return ["No major continuity breaks detected in the current transition."]
        return [issue["message"] for issue in issues]
