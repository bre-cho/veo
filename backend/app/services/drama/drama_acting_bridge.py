"""drama_acting_bridge — integrates Drama Engine output with Avatar Acting Model input.

Item 21: The Drama Engine does NOT replace the Avatar Acting Model.  Instead it
produces *living* causal context that the Avatar Acting Model consumes to enrich
its per-character acting decisions.

Responsibility split
--------------------
Drama Engine  →  *why* (motivation, fear, control intent, relationship change,
                 scene winner/loser)
Avatar Model  →  *how* (eye gaze, pause timing, gesture density, vocal
                 pressure, mask / openness expression)

This bridge translates the rich Drama compile output into the exact input format
expected by ``AvatarActingEngine.build()``.
"""
from __future__ import annotations

from typing import Any


# Mapping from Drama archetype to Avatar Acting archetype key
_DRAMA_TO_ACTING_ARCHETYPE: dict[str, str] = {
    "mentor": "mentor",
    "manipulator": "manipulator",
    "rebel": "rebel",
    "wounded_observer": "wounded_observer",
    "authority": "authority",
    "observer": "mentor",
}

# Drama primary emotion → Avatar Acting primary emotion label translation
_DRAMA_EMOTION_TO_ACTING: dict[str, str] = {
    "anger": "anger",
    "fear": "threatened",
    "shame": "shame",
    "desire": "hopeful",
    "hurt": "hurt",
    "dominance": "confident",
    "calm": "calm",
}

# Power position → acting gaze / movement hints
_POWER_POSITION_HINTS: dict[str, dict[str, str]] = {
    "dominant": {
        "gaze_style": "top_down",
        "movement": "economical",
        "pause_style": "strategic",
    },
    "threatened": {
        "gaze_style": "avoid_sustained_contact",
        "movement": "contracted_minimal",
        "pause_style": "frequent",
    },
    "rising": {
        "gaze_style": "direct_confrontational",
        "movement": "body_leads_words",
        "pause_style": "short",
    },
    "collapsed": {
        "gaze_style": "downward",
        "movement": "withdrawn",
        "pause_style": "long",
    },
    "neutral": {
        "gaze_style": "attentive_neutral",
        "movement": "moderate",
        "pause_style": "measured",
    },
}


class DramaActingBridge:
    """Converts Drama Engine compile output into Avatar Acting Model input payloads.

    Usage
    -----
    bridge = DramaActingBridge()
    acting_inputs = bridge.build_acting_inputs(drama_result)
    # → list of dicts, each ready for AvatarActingEngine.build()
    """

    def build_acting_inputs(
        self,
        drama_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Convert a DramaCompilerService.compile() result into per-character
        Avatar Acting Model inputs.

        Parameters
        ----------
        drama_result:
            Dict returned by ``DramaCompilerService.compile()``.

        Returns
        -------
        list[dict]
            One entry per character.  Each entry has the shape::

                {
                    "character_id": str,
                    "avatar_profile": dict,   # ready for AvatarActingEngine
                    "beat": dict,             # enriched beat for Acting Model
                    "relationship_state": dict | None,
                    "memory_traces": list,
                    "drama_context": dict,    # why this character acts this way
                }
        """
        scene_drama = drama_result.get("scene_drama", {})
        character_acting = drama_result.get("character_acting", [])
        power_shifts = drama_result.get("power_shifts", [])
        inner_state_updates = drama_result.get("inner_state_updates", [])
        arc_updates = drama_result.get("arc_updates", [])
        dialogue_subtexts = drama_result.get("dialogue_subtexts", [])
        tension_analysis = drama_result.get("tension_analysis", {})
        relationships: list[dict[str, Any]] = drama_result.get("relationships", [])

        # Build quick-lookup maps
        state_update_map: dict[str, dict[str, Any]] = {
            u["character_id"]: u for u in inner_state_updates
        }
        arc_map: dict[str, dict[str, Any]] = {
            a["character_id"]: a for a in arc_updates
        }
        subtext_map: dict[str, str] = {
            d["character_id"]: d.get("subtext_label", "direct")
            for d in dialogue_subtexts
        }

        results: list[dict[str, Any]] = []
        for acting_entry in character_acting:
            cid = acting_entry["character_id"]
            emotion_state = acting_entry.get("emotion_state", {})
            power_position = acting_entry.get("power_position", "neutral")
            inner_update = state_update_map.get(cid, {})
            arc = arc_map.get(cid, {})
            subtext_label = subtext_map.get(cid, "direct")

            # Build the drama_context (the "why") surfaced to Acting Model
            drama_context = self._build_drama_context(
                character_id=cid,
                acting_entry=acting_entry,
                scene_drama=scene_drama,
                inner_update=inner_update,
                arc=arc,
                power_shifts=power_shifts,
                tension_analysis=tension_analysis,
            )

            # Build the enriched avatar_profile for AvatarActingEngine
            avatar_profile = self._build_avatar_profile(
                acting_entry=acting_entry,
                emotion_state=emotion_state,
                power_position=power_position,
                drama_context=drama_context,
            )

            # Build the enriched beat for AvatarActingEngine
            beat = self._build_acting_beat(
                acting_entry=acting_entry,
                scene_drama=scene_drama,
                subtext_label=subtext_label,
                tension_analysis=tension_analysis,
            )

            # Collect all relationship edges involving this character
            char_relationships = [
                r for r in (relationships or [])
                if r.get("source_character_id") == cid or r.get("target_character_id") == cid
            ]
            primary_relationship = char_relationships[0] if char_relationships else None

            results.append({
                "character_id": cid,
                "avatar_profile": avatar_profile,
                "beat": beat,
                "relationship_state": primary_relationship,
                "memory_traces": [],
                "drama_context": drama_context,
            })

        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_drama_context(
        self,
        *,
        character_id: str,
        acting_entry: dict[str, Any],
        scene_drama: dict[str, Any],
        inner_update: dict[str, Any],
        arc: dict[str, Any],
        power_shifts: list[dict[str, Any]],
        tension_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """Build the causal context the Acting Model needs to understand *why*."""
        # Scene winner/loser determination
        dominant_id = scene_drama.get("dominant_character_id")
        is_winner = character_id == dominant_id
        outcome_type = scene_drama.get("outcome_type", "neutral")

        # Relevant power shifts for this character
        char_power_shifts = [
            ps for ps in power_shifts
            if ps.get("from_character_id") == character_id
            or ps.get("to_character_id") == character_id
        ]
        net_power_delta = sum(
            ps.get("magnitude", 0.0) * (1 if ps.get("to_character_id") == character_id else -1)
            for ps in char_power_shifts
        )

        return {
            "character_id": character_id,
            # Why this character acts this way
            "scene_motivation": acting_entry.get("scene_goal", ""),
            "hidden_fear": inner_update.get("updated_state", {}).get("fear_level", 0.0),
            "control_intent": acting_entry.get("power_position", "neutral"),
            "scene_subtext": acting_entry.get("subtext", ""),
            # Relationship / power dynamics
            "is_scene_dominant": is_winner,
            "net_power_delta": round(net_power_delta, 3),
            "outcome_type": outcome_type,
            # Arc momentum
            "arc_stage": arc.get("arc_stage", "ordinary_world"),
            "mask_break_level": arc.get("mask_break_level", 0.0),
            "collapse_risk": arc.get("collapse_risk", 0.0),
            # Scene context
            "scene_temperature": tension_analysis.get("scene_temperature", "cold"),
            "pressure_level": tension_analysis.get("pressure_level", 0.0),
            "visible_conflict": scene_drama.get("visible_conflict"),
            "hidden_conflict": scene_drama.get("hidden_conflict"),
            "turning_point": scene_drama.get("scene_turning_point"),
        }

    def _build_avatar_profile(
        self,
        *,
        acting_entry: dict[str, Any],
        emotion_state: dict[str, Any],
        power_position: str,
        drama_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Build an avatar_profile dict enriched with drama context for AvatarActingEngine."""
        # Determine archetype from body language / existing acting entry
        archetype = "observer"
        body_language = acting_entry.get("body_language", "")
        if "authority" in body_language or "erect" in body_language:
            archetype = "authority"
        elif "forward_expansive" in body_language or "explode" in acting_entry.get("reaction_pattern", ""):
            archetype = "rebel"
        elif "contracted" in body_language:
            archetype = "wounded_observer"
        elif "lean" in body_language and "manipul" in acting_entry.get("reaction_pattern", ""):
            archetype = "manipulator"

        power_hints = _POWER_POSITION_HINTS.get(power_position, _POWER_POSITION_HINTS["neutral"])

        # Map drama primary emotion to acting emotion
        drama_primary = emotion_state.get("primary_emotion", "calm")
        acting_primary = _DRAMA_EMOTION_TO_ACTING.get(drama_primary, drama_primary)

        profile: dict[str, Any] = {
            "avatar_id": acting_entry["character_id"],
            "archetype": _DRAMA_TO_ACTING_ARCHETYPE.get(archetype, archetype),
            "gaze_style": power_hints["gaze_style"],
            "pause_style": power_hints["pause_style"],
            "current_emotional_state": {
                "primary_emotion": acting_primary,
                "secondary_emotion": None,
                "tension_level": drama_context.get("pressure_level", 0.0),
                "control_level": 1.0 - float(emotion_state.get("vulnerability_level") or 0.3),
                "openness_level": 1.0 - float(drama_context.get("mask_break_level") or 0.0),
                "emotional_mask": (
                    "intact" if float(drama_context.get("mask_break_level") or 0.0) < 0.3
                    else "cracking" if float(drama_context.get("mask_break_level") or 0.0) < 0.7
                    else "broken"
                ),
                "current_need": drama_context.get("scene_motivation"),
                "scene_goal": drama_context.get("scene_motivation"),
            },
            # Drama-derived hints for the Acting Model
            "drama_context": drama_context,
        }
        return profile

    def _build_acting_beat(
        self,
        *,
        acting_entry: dict[str, Any],
        scene_drama: dict[str, Any],
        subtext_label: str,
        tension_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """Build a beat dict enriched with Drama Engine context for AvatarActingEngine."""
        return {
            "type": scene_drama.get("outcome_type", "neutral"),
            "conflict_intensity": tension_analysis.get("pressure_level", 0.5),
            "pressure_level": tension_analysis.get("pressure_level", 0.5),
            "spoken_intent": subtext_label,
            "scene_goal": acting_entry.get("scene_goal", ""),
            "outcome_type": scene_drama.get("outcome_type", "neutral"),
            "visible_conflict": scene_drama.get("visible_conflict"),
            "hidden_conflict": scene_drama.get("hidden_conflict"),
            "turning_point": scene_drama.get("scene_turning_point"),
            "key_secret": scene_drama.get("key_secret_in_play"),
            # Acting-model-specific hints derived from drama
            "micro_expression_hint": acting_entry.get("micro_expression"),
            "body_language_hint": acting_entry.get("body_language"),
            "reaction_pattern_hint": acting_entry.get("reaction_pattern"),
            "line_delivery_hint": acting_entry.get("line_delivery", {}),
        }
