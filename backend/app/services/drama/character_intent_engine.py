"""character_intent_engine — resolves each character's scene goal and hidden need.

For each character in a scene, the engine derives:
- outer_goal : what the character appears to want
- hidden_goal: what the character actually wants (often conflicts with outer)
- scene_objective: the specific tactical goal for this beat
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Goal resolution tables
# ---------------------------------------------------------------------------

_BEAT_TYPE_GOAL_MAP: dict[str, str] = {
    "interrogation": "hide_truth",
    "betrayal_reveal": "deflect_blame",
    "confession": "seek_absolution",
    "seduction": "gain_control",
    "confrontation": "maintain_dominance",
    "reconciliation": "restore_safety",
    "negotiation": "maximize_leverage",
    "farewell": "leave_on_own_terms",
    "revelation": "control_narrative",
    "reunion": "assess_threat_level",
}

_ARCHETYPE_DEFAULT_GOAL: dict[str, str] = {
    "mentor": "guide_toward_truth",
    "manipulator": "maintain_control",
    "rebel": "break_the_frame",
    "wounded_observer": "survive_unseen",
    "authority": "preserve_order",
    "observer": "gather_information",
}


class CharacterIntentEngine:
    """Resolves scene goal and hidden intent for a single character."""

    def resolve(
        self,
        character_profile: dict[str, Any],
        beat: dict[str, Any],
        character_state: dict[str, Any] | None = None,
        relationship_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return intent payload for a character in a given beat.

        Parameters
        ----------
        character_profile:
            Dict matching ``CharacterProfileSchema``.
        beat:
            Story beat dict.
        character_state:
            Optional current mutable state of the character.
        relationship_state:
            Optional relationship dict toward the scene's primary counterpart.

        Returns
        -------
        dict with keys: scene_objective, hidden_goal, outer_goal, desire_pressure
        """
        beat_type = str(beat.get("type") or "")
        archetype = str(character_profile.get("archetype") or "observer")
        dominance = float((character_state or {}).get("dominance_level") or
                          character_profile.get("dominance_baseline") or 0.5)
        rel_trust = float((relationship_state or {}).get("trust_level") or 0.5)

        # Scene objective (tactical)
        scene_objective = _BEAT_TYPE_GOAL_MAP.get(beat_type)
        if scene_objective is None:
            if dominance < 0.3:
                scene_objective = "recover_power"
            elif rel_trust < 0.3:
                scene_objective = "assess_threat"
            else:
                scene_objective = _ARCHETYPE_DEFAULT_GOAL.get(archetype, "maintain_position")

        # Hidden goal (always from the character's deepest need)
        hidden_need = str(character_profile.get("hidden_need") or "")
        hidden_goal = hidden_need or "be_seen_safely"

        # Outer goal (publicly legible motivation)
        outer_goal = str(character_profile.get("outer_goal") or "complete_the_scene")

        # How much pressure the character feels to achieve their desire
        desire_pressure = min(
            1.0,
            float(beat.get("conflict_intensity") or 0.5) * (1.0 + (0.5 - dominance))
        )

        return {
            "scene_objective": scene_objective,
            "hidden_goal": hidden_goal,
            "outer_goal": outer_goal,
            "desire_pressure": round(desire_pressure, 3),
        }
