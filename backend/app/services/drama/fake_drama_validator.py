"""fake_drama_validator — enforces 5 anti-fake-drama rules (item 23).

Rules
-----
Rule 1  All characters must NOT speak with the same articulation level / rhythm.
Rule 2  Not every scene can be explosive — drama needs restraint, silence,
        micro-shift, delayed reaction.
Rule 3  Power must NOT be expressed only through shouting.  Real power is
        silence, holding frame, not explaining, forcing the other to expose.
Rule 4  Betrayal must NOT happen without pressure, incentive, fear, or prior crack.
Rule 5  State must NOT reset unrealistically between scenes.
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Individual rule checkers
# ---------------------------------------------------------------------------

def _check_rule1_articulation_diversity(
    character_acting: list[dict[str, Any]],
) -> str | None:
    """Rule 1: All characters must NOT have the same speech tempo / articulation."""
    if len(character_acting) < 2:
        return None  # need at least 2 characters to compare

    tempos = []
    for ca in character_acting:
        line_delivery = ca.get("line_delivery") or {}
        tempo = str(line_delivery.get("tempo") or "moderate")
        tempos.append(tempo)

    if len(set(tempos)) == 1:
        return (
            "rule1_same_articulation: all characters share identical speech "
            f"tempo '{tempos[0]}' — differentiate articulation levels."
        )
    return None


def _check_rule2_no_constant_explosion(
    scene_drama: dict[str, Any],
    tension_analysis: dict[str, Any],
    scene_history: list[dict[str, Any]] | None = None,
) -> str | None:
    """Rule 2: Not every scene can be explosive.

    Flags if: this scene is explosive AND the previous scene was also explosive.
    Also flags if 3+ consecutive scenes in history are heated/explosive.
    """
    current_temp = scene_drama.get("scene_temperature") or tension_analysis.get("scene_temperature", "cold")

    if not scene_history:
        return None  # no history to compare against

    heated_temps = {"explosive", "heated"}
    previous_temp = scene_history[-1].get("scene_temperature") or scene_history[-1].get("temperature", "cold")

    if current_temp in heated_temps and previous_temp in heated_temps:
        return (
            "rule2_constant_explosion: scene is "
            f"'{current_temp}' and the previous scene was also "
            f"'{previous_temp}' — insert restraint, silence or micro-shift."
        )

    recent_temps = [
        h.get("scene_temperature") or h.get("temperature", "cold")
        for h in scene_history[-3:]
    ]

    if (
        current_temp in heated_temps
        and len(recent_temps) == 3
        and all(t in heated_temps for t in recent_temps)
    ):
        return (
            "rule2_constant_explosion: scene is "
            f"'{current_temp}' after 3 consecutive previous heated/explosive scenes "
            "— insert restraint, silence or micro-shift."
        )
    return None


def _check_rule3_power_via_noise(
    character_acting: list[dict[str, Any]],
    characters: list[dict[str, Any]] | None = None,
) -> str | None:
    """Rule 3: Power must NOT be expressed only through shouting.

    Flags when a 'dominant' character's line delivery uses 'sharp_rising'
    voice pressure without any 'strategic' pause — a sign of noise-based power.
    """
    for ca in character_acting:
        if ca.get("power_position") != "dominant":
            continue
        line_delivery = ca.get("line_delivery") or {}
        voice_pressure = str(line_delivery.get("voice_pressure") or "")
        pause = str(line_delivery.get("pause") or "")

        noisy_pressure = voice_pressure in {"sharp_rising", "high_sharp"}
        no_strategic_pause = "strategic" not in pause and "long" not in pause

        if noisy_pressure and no_strategic_pause:
            return (
                f"rule3_power_via_noise: dominant character "
                f"'{ca['character_id']}' expresses power only through sharp "
                "vocal pressure without strategic silence — true power holds frame."
            )
    return None


def _check_rule4_unearned_betrayal(
    inner_state_updates: list[dict[str, Any]],
    relationships: list[dict[str, Any]] | None = None,
) -> str | None:
    """Rule 4: Betrayal must NOT happen without prior pressure, incentive or fear.

    Flags when outcome_type contains 'betrayal' but the character state shows
    low fear, low pressure, and the relationship shows no prior crack.
    """
    for upd in inner_state_updates:
        outcome = str(upd.get("outcome_type") or "")
        if "betrayal" not in outcome:
            continue

        updated_state = upd.get("updated_state", {})
        fear_level = float(updated_state.get("fear_level") or 0.0)
        goal_pressure = float(updated_state.get("goal_pressure_level") or 0.0)
        internal_conflict = float(updated_state.get("internal_conflict_level") or 0.0)

        # Check for prior crack in relationships
        cid = upd.get("character_id", "")
        prior_crack = False
        for rel in (relationships or []):
            if rel.get("source_character_id") == cid:
                if float(rel.get("unresolved_tension_score") or 0.0) > 0.3:
                    prior_crack = True
                    break
                if float(rel.get("resentment_level") or 0.0) > 0.3:
                    prior_crack = True
                    break

        has_cause = fear_level > 0.3 or goal_pressure > 0.5 or internal_conflict > 0.3 or prior_crack
        if not has_cause:
            return (
                f"rule4_unearned_betrayal: character '{cid}' commits betrayal "
                "without sufficient fear/pressure/prior_crack — add motivation first."
            )
    return None


def _check_rule5_state_reset(
    inner_state_updates: list[dict[str, Any]],
    previous_states: dict[str, dict[str, Any]] | None = None,
) -> str | None:
    """Rule 5: State must NOT reset unrealistically between scenes.

    Flags when a character's shame/anger/fear drops more than 0.5 in one scene
    without a corresponding healing outcome (e.g., confession, forgiveness).
    """
    if not previous_states:
        return None

    healing_outcomes = {"confession", "forgiveness", "catharsis", "resolution", "reconciliation"}

    for upd in inner_state_updates:
        cid = upd.get("character_id", "")
        outcome = str(upd.get("outcome_type") or "")
        prev_state = previous_states.get(cid)
        if not prev_state:
            continue

        updated_state = upd.get("updated_state", {})
        for emotion_key in ("shame_level", "anger_level", "fear_level"):
            prev_val = float(prev_state.get(emotion_key) or 0.0)
            curr_val = float(updated_state.get(emotion_key) or 0.0)
            drop = prev_val - curr_val
            if drop > 0.5 and not any(h in outcome for h in healing_outcomes):
                return (
                    f"rule5_state_reset: character '{cid}' {emotion_key} dropped "
                    f"{drop:.2f} without a healing outcome — avoid unrealistic resets."
                )
    return None


# ---------------------------------------------------------------------------
# Main validator
# ---------------------------------------------------------------------------

class FakeDramaValidator:
    """Validates a DramaCompilerService result against the 5 anti-fake-drama rules.

    Usage
    -----
    validator = FakeDramaValidator()
    violations = validator.validate(
        drama_result=result,
        scene_history=[prev_scene_drama1, prev_scene_drama2],
        previous_states={"char_a": {...}, "char_b": {...}},
    )
    """

    def validate(
        self,
        *,
        drama_result: dict[str, Any],
        scene_history: list[dict[str, Any]] | None = None,
        previous_states: dict[str, dict[str, Any]] | None = None,
        characters: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        """Run all 5 anti-fake-drama rules and return list of violation strings.

        Parameters
        ----------
        drama_result:
            Dict returned by DramaCompilerService.compile().
        scene_history:
            List of previous scene_drama dicts (oldest first).
        previous_states:
            Mapping of character_id → state dict from the *previous* scene.
        characters:
            Character profile dicts (used by rule 3).

        Returns
        -------
        list[str]
            Zero or more violation strings.  Empty list = clean scene.
        """
        scene_drama = drama_result.get("scene_drama", {})
        tension_analysis = drama_result.get("tension_analysis", {})
        character_acting = drama_result.get("character_acting", [])
        inner_state_updates = drama_result.get("inner_state_updates", [])
        relationships = drama_result.get("relationships", [])

        violations: list[str] = []

        r1 = _check_rule1_articulation_diversity(character_acting)
        if r1:
            violations.append(r1)

        r2 = _check_rule2_no_constant_explosion(scene_drama, tension_analysis, scene_history)
        if r2:
            violations.append(r2)

        r3 = _check_rule3_power_via_noise(character_acting, characters)
        if r3:
            violations.append(r3)

        r4 = _check_rule4_unearned_betrayal(inner_state_updates, relationships)
        if r4:
            violations.append(r4)

        r5 = _check_rule5_state_reset(inner_state_updates, previous_states)
        if r5:
            violations.append(r5)

        return violations
