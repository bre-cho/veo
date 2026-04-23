"""avatar_subtext_engine — generates the hidden intent beneath spoken dialogue.

Subtext is what the character *actually* means versus what they say.
It is the primary depth signal for shot framing and micro-expression choices.
"""
from __future__ import annotations

from typing import Any


# Maps (spoken_intent, primary_emotion) → subtext
_SUBTEXT_MAP: dict[tuple[str, str], str] = {
    ("reassure", "fear"): "please_stop_looking_deeper",
    ("reassure", "guarded"): "do_not_push_further",
    ("attack", "shame"): "hurt_them_before_they_see_me",
    ("attack", "hurt"): "make_them_feel_what_i_feel",
    ("agree", "resentment"): "i_remember_what_you_did",
    ("agree", "guarded"): "i_am_buying_time",
    ("confess", "shame"): "please_still_accept_me",
    ("confess", "vulnerable"): "i_need_you_to_carry_this_too",
    ("threaten", "threatened"): "i_am_cornered_and_scared",
    ("deflect", "defensive"): "i_cannot_face_what_you_are_saying",
    ("flatter", "manipulative"): "i_want_something_from_you",
    ("joke", "defensive"): "this_topic_is_too_dangerous",
}


class AvatarSubtextEngine:
    """Generates subtext signal from spoken intent and emotional state."""

    def generate(
        self,
        spoken_intent: str,
        emotion_state: dict[str, Any],
    ) -> str:
        """Return a subtext label for use in shot and micro-expression selection.

        Parameters
        ----------
        spoken_intent:
            High-level verbal intent (e.g. ``"reassure"``, ``"attack"``).
        emotion_state:
            Current emotional state dict with ``primary_emotion`` key.
        """
        primary: str = str(emotion_state.get("primary_emotion") or "calm")
        key = (spoken_intent, primary)

        if key in _SUBTEXT_MAP:
            return _SUBTEXT_MAP[key]

        # Fallback: check secondary emotion
        secondary: str = str(emotion_state.get("secondary_emotion") or "")
        key2 = (spoken_intent, secondary)
        if key2 in _SUBTEXT_MAP:
            return _SUBTEXT_MAP[key2]

        return "direct"
