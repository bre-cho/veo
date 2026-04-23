"""avatar_motivation_engine — resolves an avatar's active scene goal.

Scene goal is the primary dramatic objective the avatar is pursuing within
the current beat.  It drives subtext generation and blocking decisions.
"""
from __future__ import annotations

from typing import Any


# Default scene goals keyed by beat type
_BEAT_GOAL_MAP: dict[str, str] = {
    "interrogation": "hide_truth",
    "betrayal_reveal": "deflect_blame",
    "accusation": "deny_and_reframe",
    "confession": "seek_forgiveness",
    "victory": "consolidate_power",
    "defeat": "save_face",
    "threat": "neutralise_threat",
    "manipulation": "control_perception",
    "reconciliation": "rebuild_trust",
    "revelation": "manage_impact",
    "exposition": "establish_authority",
}

# Fallback goal modifiers driven by relationship dominance
_LOW_DOMINANCE_GOAL = "recover_power"
_HIGH_DOMINANCE_GOAL = "maintain_control"


class AvatarMotivationEngine:
    """Resolves the avatar's in-scene dramatic goal."""

    def resolve_scene_goal(
        self,
        acting_profile: dict[str, Any],
        beat: dict[str, Any],
        relationship_state: dict[str, Any] | None = None,
    ) -> str:
        """Return a string scene goal for the current beat.

        Parameters
        ----------
        acting_profile:
            Dict representation of ``AvatarActingProfileSchema``.
        beat:
            Story beat dict.
        relationship_state:
            Optional dict with ``dominance_level`` key.
        """
        beat_type: str = beat.get("beat_type") or beat.get("type") or ""

        if beat_type in _BEAT_GOAL_MAP:
            return _BEAT_GOAL_MAP[beat_type]

        # Fallback: use relationship dominance
        dominance: float = float((relationship_state or {}).get("dominance_level", 0.5))
        if dominance < 0.3:
            return _LOW_DOMINANCE_GOAL
        return _HIGH_DOMINANCE_GOAL
