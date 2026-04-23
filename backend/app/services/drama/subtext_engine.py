"""subtext_engine — derives real intent underneath spoken dialogue.

In drama, what a character says and what they mean are often different.
The subtext engine maps (spoken_intent × emotional_state × relationship) →
a subtext label consumed by the render/acting pipeline.
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Subtext resolution tables
# ---------------------------------------------------------------------------

_SPOKEN_EMOTION_SUBTEXT: dict[tuple[str, str], str] = {
    ("reassure", "fear"): "please_stop_looking_deeper",
    ("reassure", "shame"): "i_need_you_to_believe_me",
    ("attack", "shame"): "hurt_them_before_they_see_me",
    ("attack", "hurt"): "make_them_feel_what_i_feel",
    ("apologise", "anger"): "i_am_not_really_sorry",
    ("apologise", "shame"): "i_need_forgiveness_to_survive",
    ("deflect", "fear"): "do_not_come_closer",
    ("deflect", "shame"): "change_the_subject_now",
    ("question", "threatened"): "i_already_know_the_answer",
    ("question", "guarded"): "testing_your_loyalty",
    ("confess", "shame"): "please_still_accept_me",
    ("confess", "relief"): "finally_releasing_the_weight",
    ("seduce", "fear"): "control_through_desire",
    ("seduce", "dominance"): "i_choose_who_has_access_to_me",
    ("laugh", "hurt"): "covering_pain_with_performance",
    ("laugh", "guarded"): "deflecting_with_charm",
    ("lecture", "shame"): "i_must_prove_my_worth",
    ("lecture", "dominance"): "you_exist_inside_my_frame",
    ("withdraw", "hurt"): "you_cannot_reach_what_i_hide",
    ("withdraw", "threatened"): "i_am_already_gone",
}

_RELATIONSHIP_TRUST_OVERRIDE: dict[str, str] = {
    "hide_truth": "i_cannot_let_you_know",
    "test_loyalty": "prove_you_are_safe",
    "establish_dominance": "you_will_accept_my_terms",
    "seek_comfort": "i_need_you_but_cannot_say_so",
}


class DramaSubtextEngine:
    """Generates subtext label for a character's dialogue turn."""

    def generate(
        self,
        spoken_intent: str,
        primary_emotion: str,
        scene_objective: str | None = None,
        relationship_state: dict[str, Any] | None = None,
    ) -> str:
        """Derive the subtext label.

        Parameters
        ----------
        spoken_intent:
            What the character explicitly does (e.g. "reassure", "attack").
        primary_emotion:
            The character's current primary emotion.
        scene_objective:
            Optional resolved scene goal from CharacterIntentEngine.
        relationship_state:
            Optional relationship dict to target entity.

        Returns
        -------
        str — a slug describing the hidden meaning.
        """
        key = (spoken_intent.lower(), primary_emotion.lower())
        result = _SPOKEN_EMOTION_SUBTEXT.get(key)

        if result is None and scene_objective:
            result = _RELATIONSHIP_TRUST_OVERRIDE.get(scene_objective)

        if result is None and relationship_state:
            trust = float(relationship_state.get("trust_level") or 0.5)
            if trust < 0.3:
                result = "speaking_but_not_trusting"
            elif trust > 0.8:
                result = "direct"

        return result or "direct"
