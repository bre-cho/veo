"""avatar_reaction_engine — maps pressure + defense mechanism → behavioral reaction.

When an avatar is under pressure, its defense mechanism determines the
physical and vocal reaction pattern.  This drives blocking, gaze, and
line delivery in the render payload.
"""
from __future__ import annotations

from typing import Any


# Maps defense_mechanism → (low_pressure_reaction, high_pressure_reaction)
_DEFENSE_REACTIONS: dict[str, tuple[str, str]] = {
    "withdrawal": (
        "controlled_stillness",
        "look_away_silence_step_back",
    ),
    "attack": (
        "hold_ground_steady_gaze",
        "interrupt_hard_stare_step_forward",
    ),
    "joke": (
        "light_smile_topic_pivot",
        "smirk_deflect_change_topic",
    ),
    "denial": (
        "confident_posture_direct_eye",
        "raised_chin_over_explain",
    ),
    "rationalize": (
        "measured_explanation",
        "fast_talk_hands_forward",
    ),
    "seduce": (
        "soft_eye_contact_lean_in",
        "mirror_body_lower_voice",
    ),
    "freeze": (
        "micro_pause_before_response",
        "complete_stillness_blank_face",
    ),
    "confess": (
        "downward_gaze_slower_speech",
        "full_eye_contact_voice_break",
    ),
    "explode": (
        "clipped_speech_tension_in_jaw",
        "sharp_volume_spike_forward_lean",
    ),
}

_DEFAULT_NEUTRAL = "neutral_controlled_response"


class AvatarReactionEngine:
    """Maps acting profile + pressure level → behavioral reaction pattern."""

    def react(
        self,
        acting_profile: dict[str, Any],
        emotion_state: dict[str, Any],
        pressure_level: float,
    ) -> str:
        """Return a reaction pattern string.

        Parameters
        ----------
        acting_profile:
            Dict with ``defense_mechanism`` key.
        emotion_state:
            Current emotional state dict; ``tension_level`` amplifies pressure.
        pressure_level:
            External pressure applied to the avatar (0–1).
        """
        defense: str = str(acting_profile.get("defense_mechanism") or "withdrawal")
        tension: float = float(emotion_state.get("tension_level") or 0.0)

        # Effective pressure combines external pressure and internal tension
        effective_pressure = min(1.0, pressure_level * 0.6 + tension * 0.4)

        low_reaction, high_reaction = _DEFENSE_REACTIONS.get(
            defense, (_DEFAULT_NEUTRAL, _DEFAULT_NEUTRAL)
        )

        if effective_pressure >= 0.7:
            return high_reaction
        if effective_pressure >= 0.3:
            return low_reaction
        return _DEFAULT_NEUTRAL
