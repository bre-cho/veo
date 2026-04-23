"""drama_compiler_service — orchestrates the full Multi-Character Drama Engine.

Pipeline
--------
DramaCompileRequest
    → CharacterIntentEngine   (per-character goal/hidden-need)
    → TensionEngine           (scene temperature + pressure)
    → DramaSubtextEngine      (spoken vs. real intent per character)
    → PowerShiftEngine        (power deltas from beat outcome)
    → RelationshipEngine      (chemistry detection)
    → CameraDramaEngine       (blocking + shot directives)
    → EmotionalUpdateEngine   (inner state update per character)
    → ArcEngine               (arc stage advance)
    → DramaContinuityEngine   (scene law validation)
    → DramaCompileResponse    (full structured output)

Design notes
------------
- All engines are pure-function style (no DB calls inside engines).
- The service is responsible for DB persistence if a session is provided.
- The response is fully serialisable; callers inject it into scene_payload.
"""
from __future__ import annotations

from typing import Any

from app.services.drama.arc_engine import ArcEngine
from app.services.drama.camera_drama_engine import CameraDramaEngine
from app.services.drama.character_intent_engine import CharacterIntentEngine
from app.services.drama.continuity_engine import DramaContinuityEngine
from app.services.drama.emotional_update_engine import EmotionalUpdateEngine
from app.services.drama.power_shift_engine import PowerShiftEngine
from app.services.drama.relationship_engine import RelationshipEngine
from app.services.drama.subtext_engine import DramaSubtextEngine
from app.services.drama.tension_engine import TensionEngine


# ---------------------------------------------------------------------------
# Archetype acting preset lookup (mirrors avatar_acting_engine presets)
# ---------------------------------------------------------------------------

_ARCHETYPE_MICRO_EXPRESSION: dict[str, str] = {
    "mentor": "calm_thoughtful",
    "manipulator": "micro_smile_soft_eyes",
    "rebel": "jaw_forward_wide_eyes",
    "wounded_observer": "tight_lips_downcast_eyes",
    "authority": "neutral_controlled",
    "observer": "attentive_neutral",
}

_ARCHETYPE_BODY_LANGUAGE: dict[str, str] = {
    "mentor": "open_grounded",
    "manipulator": "slight_lean_relaxed_hands",
    "rebel": "weight_forward_expansive",
    "wounded_observer": "contracted_minimal_movement",
    "authority": "still_erect_centred",
    "observer": "neutral_balanced",
}

_ARCHETYPE_REACTION: dict[str, str] = {
    "mentor": "absorb_then_reframe",
    "manipulator": "deflect_seduce_reframe",
    "rebel": "explode_or_exit",
    "wounded_observer": "silence_swallow_feeling",
    "authority": "look_down_slow_tighten",
    "observer": "neutral_controlled_response",
}


def _default_state(character_id: str, project_id: str) -> dict[str, Any]:
    return {
        "character_id": character_id,
        "project_id": project_id,
        "emotional_valence": 0.0,
        "arousal": 0.5,
        "control_level": 0.5,
        "dominance_level": 0.5,
        "vulnerability_level": 0.3,
        "trust_level": 0.5,
        "shame_level": 0.0,
        "anger_level": 0.0,
        "fear_level": 0.0,
        "desire_level": 0.3,
        "mask_strength": 0.7,
        "openness_level": 0.3,
        "internal_conflict_level": 0.0,
        "goal_pressure_level": 0.5,
        "current_subtext": None,
        "current_secret_load": 0.0,
        "current_power_position": "neutral",
        "updated_from_previous_scene": False,
    }


class DramaCompilerService:
    """Single-entry-point orchestrator for the Multi-Character Drama Engine."""

    def __init__(self) -> None:
        self._intent_engine = CharacterIntentEngine()
        self._tension_engine = TensionEngine()
        self._subtext_engine = DramaSubtextEngine()
        self._power_shift_engine = PowerShiftEngine()
        self._relationship_engine = RelationshipEngine()
        self._camera_engine = CameraDramaEngine()
        self._emotional_update = EmotionalUpdateEngine()
        self._arc_engine = ArcEngine()
        self._continuity_engine = DramaContinuityEngine()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compile(
        self,
        *,
        project_id: str,
        scene_id: str,
        episode_id: str | None = None,
        beat: dict[str, Any],
        characters: list[dict[str, Any]],
        character_states: list[dict[str, Any]] | None = None,
        relationships: list[dict[str, Any]] | None = None,
        memory_traces: list[dict[str, Any]] | None = None,
        arc_progresses: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Run the full drama pipeline for one scene beat.

        Parameters
        ----------
        project_id, scene_id, episode_id:
            Scene context identifiers.
        beat:
            Story beat dict with at minimum: type, conflict_intensity,
            pressure_level, outcome_type, spoken_intent, memory_trigger.
        characters:
            List of CharacterProfileSchema-compatible dicts.
        character_states:
            Optional per-character state dicts.  Falls back to defaults.
        relationships:
            Optional list of RelationshipEdgeSchema dicts.
        memory_traces:
            Optional list of DramaMemoryTrace dicts.
        arc_progresses:
            Optional list of DramaArcProgress dicts.

        Returns
        -------
        dict compatible with ``DramaCompileResponse``.
        """
        relationships = relationships or []
        memory_traces = memory_traces or []
        arc_progresses = arc_progresses or []

        # Build state lookup
        state_map: dict[str, dict[str, Any]] = {}
        for s in (character_states or []):
            state_map[s["character_id"]] = s
        for char in characters:
            cid = char.get("id") or char.get("avatar_id") or char["name"]
            if cid not in state_map:
                state_map[cid] = _default_state(cid, project_id)

        arc_map: dict[str, dict[str, Any]] = {}
        for ap in arc_progresses:
            arc_map[ap["character_id"]] = ap

        # ── Step 1: carry-forward continuity ────────────────────────────
        recall_trigger = beat.get("memory_trigger") or beat.get("type")
        for cid, state in state_map.items():
            relevant_memories = self._continuity_engine.fetch_relevant_memories(
                cid, recall_trigger, memory_traces
            )
            state_map[cid] = self._continuity_engine.carry_forward_state(
                state, beat.get("outcome_type"), relevant_memories
            )

        # ── Step 2: tension analysis ─────────────────────────────────────
        states_list = list(state_map.values())
        tension = self._tension_engine.compute(beat, states_list, relationships)

        # ── Step 3: per-character intent + subtext ───────────────────────
        intent_map: dict[str, dict[str, Any]] = {}
        subtext_map: dict[str, str] = {}
        for char in characters:
            cid = char.get("id") or char.get("avatar_id") or char["name"]
            state = state_map[cid]

            # Pick primary relationship for this character
            primary_rel = self._pick_primary_relationship(cid, characters, relationships)

            intent = self._intent_engine.resolve(char, beat, state, primary_rel)
            intent_map[cid] = intent

            spoken_intent = str(beat.get("spoken_intent") or "inform")
            primary_emotion = self._primary_emotion_from_state(state)
            subtext = self._subtext_engine.generate(
                spoken_intent=spoken_intent,
                primary_emotion=primary_emotion,
                scene_objective=intent["scene_objective"],
                relationship_state=primary_rel,
            )
            subtext_map[cid] = subtext
            state["current_subtext"] = subtext

        # ── Step 4: scene drama assembly ─────────────────────────────────
        dominant_id, threatened_id = self._identify_power_positions(state_map, characters)
        outcome_type = str(beat.get("outcome_type") or "neutral")

        scene_drama: dict[str, Any] = {
            "scene_id": scene_id,
            "project_id": project_id,
            "episode_id": episode_id,
            "scene_goal": beat.get("scene_goal"),
            "visible_conflict": beat.get("visible_conflict"),
            "hidden_conflict": beat.get("hidden_conflict"),
            "scene_temperature": tension["scene_temperature"],
            "pressure_level": tension["pressure_level"],
            "dominant_character_id": dominant_id,
            "threatened_character_id": threatened_id,
            "emotional_center_character_id": self._emotional_center(state_map),
            "key_secret_in_play": beat.get("key_secret"),
            "scene_turning_point": beat.get("turning_point"),
            "outcome_type": outcome_type,
            "power_shift_delta": 0.0,
            "trust_shift_delta": 0.0,
            "exposure_shift_delta": 0.0,
            "dependency_shift_delta": 0.0,
            "scene_aftertaste": beat.get("aftertaste"),
        }

        # ── Step 5: power shifts ─────────────────────────────────────────
        power_shifts = self._power_shift_engine.compute(beat, scene_drama, relationships)
        if power_shifts:
            scene_drama["power_shift_delta"] = power_shifts[0].get("magnitude", 0.0)
            scene_drama["trust_shift_delta"] = abs(
                power_shifts[0].get("relationship_deltas", {}).get("trust_level", 0.0)
            )
            scene_drama["exposure_shift_delta"] = abs(
                power_shifts[0].get("relationship_deltas", {}).get("exposure_shift_delta", 0.0)
            )

        # ── Step 6: camera directives ─────────────────────────────────────
        blocking_directives: list[dict[str, Any]] = []
        for char in characters:
            cid = char.get("id") or char.get("avatar_id") or char["name"]
            state = state_map[cid]
            directive = self._camera_engine.build_directive(
                character_id=cid,
                scene_id=scene_id,
                character_state=state,
                scene_drama=scene_drama,
                subtext=subtext_map.get(cid, "direct"),
                outcome_type=outcome_type if outcome_type != "neutral" else None,
            )
            blocking_directives.append(directive)

        # ── Step 7: character acting decisions ───────────────────────────
        character_acting: list[dict[str, Any]] = []
        for char in characters:
            cid = char.get("id") or char.get("avatar_id") or char["name"]
            state = state_map[cid]
            acting = self._build_acting_output(
                character_id=cid,
                scene_id=scene_id,
                char_profile=char,
                state=state,
                intent=intent_map[cid],
                subtext=subtext_map.get(cid, "direct"),
                scene_drama=scene_drama,
                blocking=next(
                    (b for b in blocking_directives if b["character_id"] == cid), None
                ),
            )
            character_acting.append(acting)

        # ── Step 8: inner state updates ──────────────────────────────────
        inner_state_updates: list[dict[str, Any]] = []
        arc_updates: list[dict[str, Any]] = []
        for char in characters:
            cid = char.get("id") or char.get("avatar_id") or char["name"]
            state = state_map[cid]
            related_id = threatened_id if cid == dominant_id else dominant_id

            update_result = self._emotional_update.apply(
                character_id=cid,
                scene_id=scene_id,
                outcome_type=outcome_type,
                character_state=state,
                related_character_id=related_id,
                beat=beat,
            )
            state_map[cid] = update_result["updated_state"]

            inner_state_updates.append({
                "character_id": cid,
                "scene_id": scene_id,
                "outcome_type": outcome_type,
                "updated_state": update_result["updated_state"],
                "memory_trace": update_result["memory_trace"],
                "arc_stage_update": update_result["arc_stage_update"],
            })

            # Arc advance
            arc_progress = arc_map.get(cid) or {"arc_stage": "ordinary_world"}
            arc_result = self._arc_engine.evaluate(
                arc_progress, outcome_type, update_result["updated_state"]
            )
            arc_updates.append({
                "character_id": cid,
                "project_id": project_id,
                "episode_id": episode_id,
                "arc_name": arc_progress.get("arc_name", "main"),
                **arc_result,
            })

        # ── Step 9: scene law validation ─────────────────────────────────
        violations = self._continuity_engine.validate_scene_law(scene_drama)

        # ── Assemble response ─────────────────────────────────────────────
        return {
            "ok": True,
            "scene_drama": scene_drama,
            "character_acting": character_acting,
            "power_shifts": power_shifts,
            "blocking_directives": blocking_directives,
            "dialogue_subtexts": [
                {
                    "character_id": cid,
                    "spoken_intent": str(beat.get("spoken_intent") or "inform"),
                    "real_intent": intent_map[cid]["hidden_goal"],
                    "subtext_label": subtext_map[cid],
                    "scene_objective": intent_map[cid]["scene_objective"],
                }
                for cid in subtext_map
            ],
            "arc_updates": arc_updates,
            "inner_state_updates": inner_state_updates,
            "tension_analysis": tension,
            "scene_law_violations": violations,
            "metadata": {
                "character_count": len(characters),
                "relationship_count": len(relationships),
                "memory_trace_count": len(memory_traces),
            },
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _pick_primary_relationship(
        self,
        character_id: str,
        characters: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Return the most relevant relationship for this character in the scene."""
        scene_rels = [
            r for r in relationships
            if r.get("source_character_id") == character_id
        ]
        if not scene_rels:
            return None
        # Pick the one with highest unresolved tension
        return max(scene_rels, key=lambda r: float(r.get("unresolved_tension_score") or 0.0))

    def _primary_emotion_from_state(self, state: dict[str, Any]) -> str:
        scored = {
            "anger": float(state.get("anger_level") or 0.0),
            "fear": float(state.get("fear_level") or 0.0),
            "shame": float(state.get("shame_level") or 0.0),
            "desire": float(state.get("desire_level") or 0.0),
            "hurt": float(state.get("vulnerability_level") or 0.0),
            "dominance": float(state.get("dominance_level") or 0.0) - 0.5,
        }
        primary = max(scored, key=lambda k: scored[k])
        return primary if scored[primary] > 0.1 else "calm"

    def _identify_power_positions(
        self,
        state_map: dict[str, dict[str, Any]],
        characters: list[dict[str, Any]],
    ) -> tuple[str | None, str | None]:
        if len(characters) < 2:
            return None, None
        dominance_scores = {
            (c.get("id") or c.get("avatar_id") or c["name"]): float(
                state_map.get(
                    c.get("id") or c.get("avatar_id") or c["name"], {}
                ).get("dominance_level") or 0.5
            )
            for c in characters
        }
        dominant_id = max(dominance_scores, key=lambda k: dominance_scores[k])
        threatened_id = min(dominance_scores, key=lambda k: dominance_scores[k])
        return dominant_id, threatened_id

    def _emotional_center(self, state_map: dict[str, dict[str, Any]]) -> str | None:
        """Return the character with highest internal conflict (emotional focal point)."""
        if not state_map:
            return None
        return max(
            state_map,
            key=lambda k: float(state_map[k].get("internal_conflict_level") or 0.0),
        )

    def _build_acting_output(
        self,
        *,
        character_id: str,
        scene_id: str,
        char_profile: dict[str, Any],
        state: dict[str, Any],
        intent: dict[str, Any],
        subtext: str,
        scene_drama: dict[str, Any],
        blocking: dict[str, Any] | None,
    ) -> dict[str, Any]:
        archetype = str(char_profile.get("archetype") or char_profile.get("acting_preset_seed") or "observer")
        micro_expression = _ARCHETYPE_MICRO_EXPRESSION.get(archetype, "neutral")
        body_language = _ARCHETYPE_BODY_LANGUAGE.get(archetype, "neutral_balanced")
        reaction_pattern = _ARCHETYPE_REACTION.get(archetype, "neutral_controlled_response")

        # Emotion modulates micro_expression
        primary_emotion = self._primary_emotion_from_state(state)
        _EMOTION_MICRO: dict[str, str] = {
            "anger": "furrowed_brow_flared_nostrils",
            "fear": "wide_eyes_tense_neck",
            "shame": "downcast_eyes_compressed_lips",
            "hurt": "wet_eyes_tight_jaw",
            "dominance": "relaxed_jaw_steady_gaze",
        }
        if primary_emotion in _EMOTION_MICRO:
            micro_expression = _EMOTION_MICRO[primary_emotion]

        tension = float(scene_drama.get("pressure_level") or 0.0)
        tempo = "slow_then_sharp" if tension > 0.7 else "deliberate" if tension > 0.4 else "moderate"

        return {
            "character_id": character_id,
            "scene_id": scene_id,
            "emotion_state": {
                "dominance_level": state.get("dominance_level"),
                "vulnerability_level": state.get("vulnerability_level"),
                "anger_level": state.get("anger_level"),
                "fear_level": state.get("fear_level"),
                "shame_level": state.get("shame_level"),
                "primary_emotion": primary_emotion,
            },
            "scene_goal": intent["scene_objective"],
            "subtext": subtext,
            "reaction_pattern": reaction_pattern,
            "micro_expression": micro_expression,
            "body_language": body_language,
            "line_delivery": {
                "tempo": tempo,
                "voice_pressure": "compressed" if primary_emotion == "dominance" else "moderate",
            },
            "power_position": state.get("current_power_position", "neutral"),
            "camera_directive": blocking,
        }
