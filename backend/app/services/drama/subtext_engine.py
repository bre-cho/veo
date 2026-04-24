"""subtext_engine — derives real intent underneath spoken dialogue.

Section 9: Dialogue Subtext Engine
-----------------------------------
Each line has 3 layers:
  1. literal_text      — what is actually said
  2. subtext           — what the character really wants to force/hide/test
  3. psychological_action — attack / probe / withhold / seduce / shame /
                             reassure / dominate / retreat / bait / confess /
                             redirect / expose / deny / test_loyalty

In drama, what a character says and what they mean are often different.
The subtext engine maps (spoken_intent × emotional_state × relationship) →
subtext label + psychological action consumed by the render/acting pipeline.
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Dialogue act types (section 9.2)
# ---------------------------------------------------------------------------

DIALOGUE_ACT_TYPES = {
    "attack", "probe", "withhold", "seduce", "shame", "reassure",
    "dominate", "retreat", "bait", "confess", "redirect", "expose",
    "deny", "test_loyalty",
}

# ---------------------------------------------------------------------------
# Subtext resolution tables
# ---------------------------------------------------------------------------

_SPOKEN_EMOTION_SUBTEXT: dict[tuple[str, str], tuple[str, str, str]] = {
    # (spoken_intent, primary_emotion) → (subtext, hidden_intent, psychological_action)
    ("reassure", "fear"): (
        "please_stop_looking_deeper",
        "keep_them_from_seeing_my_panic",
        "withhold",
    ),
    ("reassure", "shame"): (
        "i_need_you_to_believe_me",
        "protect_my_image",
        "deny",
    ),
    ("attack", "shame"): (
        "hurt_them_before_they_see_me",
        "deflect_exposure_through_offense",
        "attack",
    ),
    ("attack", "hurt"): (
        "make_them_feel_what_i_feel",
        "equalize_the_pain",
        "attack",
    ),
    ("apologise", "anger"): (
        "i_am_not_really_sorry",
        "de-escalate_to_regain_control",
        "redirect",
    ),
    ("apologise", "shame"): (
        "i_need_forgiveness_to_survive",
        "restore_acceptance",
        "confess",
    ),
    ("deflect", "fear"): (
        "do_not_come_closer",
        "maintain_safe_distance",
        "retreat",
    ),
    ("deflect", "shame"): (
        "change_the_subject_now",
        "bury_the_evidence",
        "redirect",
    ),
    ("question", "threatened"): (
        "i_already_know_the_answer",
        "confirm_betrayal_suspicion",
        "probe",
    ),
    ("question", "guarded"): (
        "testing_your_loyalty",
        "map_their_allegiance",
        "test_loyalty",
    ),
    ("confess", "shame"): (
        "please_still_accept_me",
        "trade_truth_for_mercy",
        "confess",
    ),
    ("confess", "relief"): (
        "finally_releasing_the_weight",
        "shed_the_secret_burden",
        "confess",
    ),
    ("seduce", "fear"): (
        "control_through_desire",
        "make_them_need_me",
        "seduce",
    ),
    ("seduce", "dominance"): (
        "i_choose_who_has_access_to_me",
        "reward_loyalty_conditionally",
        "dominate",
    ),
    ("laugh", "hurt"): (
        "covering_pain_with_performance",
        "deny_vulnerability",
        "withhold",
    ),
    ("laugh", "guarded"): (
        "deflecting_with_charm",
        "lower_their_defenses",
        "bait",
    ),
    ("lecture", "shame"): (
        "i_must_prove_my_worth",
        "establish_moral_superiority",
        "shame",
    ),
    ("lecture", "dominance"): (
        "you_exist_inside_my_frame",
        "reinforce_hierarchy",
        "dominate",
    ),
    ("withdraw", "hurt"): (
        "you_cannot_reach_what_i_hide",
        "deny_them_the_satisfaction",
        "retreat",
    ),
    ("withdraw", "threatened"): (
        "i_am_already_gone",
        "pre-emptive_abandonment",
        "retreat",
    ),
    ("expose", "anger"): (
        "i_will_make_them_see_you",
        "destroy_their_cover",
        "expose",
    ),
    ("bait", "dominance"): (
        "i_want_to_see_if_you_will_fall",
        "test_their_weakness",
        "bait",
    ),
    ("probe", "fear"): (
        "i_need_to_know_what_you_know",
        "gather_intelligence_safely",
        "probe",
    ),
}

_RELATIONSHIP_TRUST_OVERRIDE: dict[str, tuple[str, str]] = {
    # scene_objective → (subtext, psychological_action)
    "hide_truth": ("i_cannot_let_you_know", "withhold"),
    "test_loyalty": ("prove_you_are_safe", "test_loyalty"),
    "establish_dominance": ("you_will_accept_my_terms", "dominate"),
    "seek_comfort": ("i_need_you_but_cannot_say_so", "bait"),
    "gather_information": ("i_am_mapping_you", "probe"),
    "break_the_frame": ("your_rules_do_not_apply_to_me", "attack"),
}


# ---------------------------------------------------------------------------
# Power move classifier
# ---------------------------------------------------------------------------

def _classify_power_move(
    psychological_action: str,
    emotional_charge: float,
    hidden_intent: str,
) -> str:
    """Map action + charge → power move description."""
    if psychological_action in {"dominate", "shame", "expose"}:
        level = "high_overt" if emotional_charge > 0.6 else "medium_overt"
        return f"{level}_power"
    if psychological_action in {"seduce", "bait", "test_loyalty"}:
        return "high_covert_power"
    if psychological_action in {"withhold", "retreat", "deny"}:
        return "passive_power"
    if psychological_action in {"confess", "reassure"}:
        return "vulnerability_as_power" if "need" in hidden_intent else "low_power"
    return "neutral_power"


class DramaSubtextEngine:
    """Generates full 3-layer subtext for a character's dialogue turn."""

    def generate(
        self,
        spoken_intent: str,
        primary_emotion: str,
        scene_objective: str | None = None,
        relationship_state: dict[str, Any] | None = None,
    ) -> str:
        """Derive the subtext label (legacy interface — returns slug only).

        Use ``generate_full`` for the complete 3-layer payload.
        """
        payload = self.generate_full(
            spoken_intent=spoken_intent,
            primary_emotion=primary_emotion,
            scene_objective=scene_objective,
            relationship_state=relationship_state,
        )
        return payload["subtext_label"]

    def generate_full(
        self,
        spoken_intent: str,
        primary_emotion: str,
        line_text: str | None = None,
        scene_objective: str | None = None,
        relationship_state: dict[str, Any] | None = None,
        speaker_id: str | None = None,
        target_id: str | None = None,
        scene_id: str | None = None,
    ) -> dict[str, Any]:
        """Return a full 3-layer DialogueSubtextFullSchema-compatible dict.

        Layers
        ------
        1. literal_text / literal_intent
        2. hidden_intent / subtext_label
        3. psychological_action + power_move
        """
        key = (spoken_intent.lower(), primary_emotion.lower())
        lookup = _SPOKEN_EMOTION_SUBTEXT.get(key)

        if lookup:
            subtext_label, hidden_intent, psychological_action = lookup
        else:
            # Fallback through scene objective
            obj_key = scene_objective or ""
            obj_lookup = _RELATIONSHIP_TRUST_OVERRIDE.get(obj_key)
            if obj_lookup:
                subtext_label = obj_lookup[0]
                hidden_intent = f"pursue_{obj_key}"
                psychological_action = obj_lookup[1]
            elif relationship_state:
                trust = float(relationship_state.get("trust") or
                              relationship_state.get("trust_level") or 0.5)
                if trust < 0.3:
                    subtext_label = "speaking_but_not_trusting"
                    hidden_intent = "maintain_facade_of_cooperation"
                    psychological_action = "withhold"
                elif trust > 0.8:
                    subtext_label = "direct"
                    hidden_intent = "genuine_communication"
                    psychological_action = "reassure"
                else:
                    subtext_label = "cautious_direct"
                    hidden_intent = "proceed_carefully"
                    psychological_action = "probe"
            else:
                subtext_label = "direct"
                hidden_intent = "communicate_clearly"
                psychological_action = "reassure"

        # Emotional charge: blend shame + vulnerability + desire
        rel = relationship_state or {}
        emotional_charge = min(1.0, round(
            float(rel.get("emotional_hook_strength") or 0.0) * 0.4
            + float(rel.get("shame_exposure_risk") or 0.0) * 0.3
            + float(rel.get("attraction") or rel.get("attraction_level") or 0.0) * 0.3,
            3,
        ))

        # Mask level: inverse of openness implied by subtext
        mask_level = 0.3 if psychological_action in {"confess", "reassure"} else (
            0.9 if psychological_action in {"withhold", "deny"} else 0.6
        )

        # Threat level
        threat_level = round(
            float(rel.get("fear") or rel.get("fear_level") or 0.0) * 0.5
            + (0.4 if psychological_action in {"attack", "expose", "shame"} else 0.0),
            3,
        )

        # Intimacy bid
        intimacy_bid = round(
            float(rel.get("attraction") or rel.get("attraction_level") or 0.0) * 0.5
            + (0.4 if psychological_action in {"seduce", "confess", "bait"} else 0.0),
            3,
        )

        power_move = _classify_power_move(psychological_action, emotional_charge, hidden_intent)

        # Honesty level
        honesty_level = 0.8 if psychological_action in {"confess"} else (
            0.1 if psychological_action in {"deny", "withhold"} else 0.5
        )

        return {
            "scene_id": scene_id,
            "speaker_id": speaker_id,
            "target_id": target_id,
            "line_text": line_text,
            "literal_intent": spoken_intent,
            "hidden_intent": hidden_intent,
            "subtext_label": subtext_label,
            "psychological_action": psychological_action,
            "dialogue_act": psychological_action,
            "emotional_charge": emotional_charge,
            "honesty_level": honesty_level,
            "mask_level": mask_level,
            "threat_level": min(1.0, threat_level),
            "intimacy_bid": min(1.0, intimacy_bid),
            "power_move": power_move,
            "expected_target_reaction": self._expected_reaction(psychological_action),
        }

    def _expected_reaction(self, action: str) -> str:
        _MAP = {
            "attack": "defend_or_counter_attack",
            "probe": "deflect_or_reveal",
            "withhold": "push_for_more",
            "seduce": "drawn_in_or_pull_back",
            "shame": "collapse_or_rage",
            "reassure": "lower_guard",
            "dominate": "submit_or_resist",
            "retreat": "pursue_or_release",
            "bait": "take_the_bait_or_catch_the_trap",
            "confess": "accept_or_reject",
            "redirect": "follow_or_resist_redirect",
            "expose": "denial_or_exposure_response",
            "deny": "press_harder_or_believe",
            "test_loyalty": "prove_loyalty_or_fail",
        }
        return _MAP.get(action, "neutral_response")
