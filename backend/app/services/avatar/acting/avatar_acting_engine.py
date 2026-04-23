"""avatar_acting_engine — orchestrates the full acting decision pipeline.

The engine combines emotional state evolution, motivation resolution, subtext
generation, and reaction mapping into a structured ``AvatarActingOutput`` that
the scene planner, shot planner, and render payload can consume directly.

Typical call chain
------------------
beat → AvatarEmotionEngine.evolve()
     → AvatarMotivationEngine.resolve_scene_goal()
     → AvatarSubtextEngine.generate()
     → AvatarReactionEngine.react()
     → assemble AvatarActingOutput

The output dict mirrors ``AvatarActingOutput`` and is injected into
``scene_plan["acting"]`` by the director pipeline.
"""
from __future__ import annotations

from typing import Any

from app.services.avatar.acting.avatar_emotion_engine import AvatarEmotionEngine
from app.services.avatar.acting.avatar_motivation_engine import AvatarMotivationEngine
from app.services.avatar.acting.avatar_reaction_engine import AvatarReactionEngine
from app.services.avatar.acting.avatar_subtext_engine import AvatarSubtextEngine

# ---------------------------------------------------------------------------
# Archetype acting presets
# ---------------------------------------------------------------------------
ARCHETYPE_PRESETS: dict[str, dict[str, Any]] = {
    "mentor": {
        "speech_tempo": "slow",
        "pause_style": "long",
        "baseline_energy": "low",
        "gaze_style": "steady",
        "micro_expression_base": "calm_thoughtful",
        "body_language_base": "open_grounded",
        "voice_pressure_base": "warm_compressed",
    },
    "manipulator": {
        "speech_tempo": "variable",
        "pause_style": "calculated",
        "baseline_energy": "medium",
        "gaze_style": "deflect_then_lock",
        "micro_expression_base": "micro_smile_soft_eyes",
        "body_language_base": "slight_lean_relaxed_hands",
        "voice_pressure_base": "smooth_low",
    },
    "rebel": {
        "speech_tempo": "fast",
        "pause_style": "short",
        "baseline_energy": "high",
        "gaze_style": "direct_confrontational",
        "micro_expression_base": "jaw_forward_wide_eyes",
        "body_language_base": "weight_forward_expansive",
        "voice_pressure_base": "sharp_high",
    },
    "wounded_observer": {
        "speech_tempo": "slow",
        "pause_style": "frequent",
        "baseline_energy": "low",
        "gaze_style": "avoidant",
        "micro_expression_base": "tight_lips_downcast_eyes",
        "body_language_base": "contracted_minimal_movement",
        "voice_pressure_base": "soft_flat",
    },
    "authority": {
        "speech_tempo": "deliberate",
        "pause_style": "strategic",
        "baseline_energy": "low",
        "gaze_style": "top_down",
        "micro_expression_base": "neutral_controlled",
        "body_language_base": "still_erect_centred",
        "voice_pressure_base": "compressed_deep",
    },
}

_DEFAULT_PRESET = ARCHETYPE_PRESETS["mentor"]


def _get_preset(acting_profile: dict[str, Any]) -> dict[str, Any]:
    archetype = str(acting_profile.get("archetype") or "mentor")
    return ARCHETYPE_PRESETS.get(archetype, _DEFAULT_PRESET)


# ---------------------------------------------------------------------------
# Micro-expression and body language helpers
# ---------------------------------------------------------------------------

_EMOTION_MICRO_EXPRESSIONS: dict[str, str] = {
    "hurt": "wet_eyes_tight_jaw",
    "anger": "furrowed_brow_flared_nostrils",
    "defensive": "lifted_chin_narrowed_eyes",
    "vulnerable": "soft_eyes_parted_lips",
    "confident": "relaxed_jaw_steady_gaze",
    "shame": "downcast_eyes_compressed_lips",
    "threatened": "wide_eyes_tense_neck",
    "guarded": "flat_expression_locked_jaw",
    "hopeful": "raised_brows_soft_smile",
    "shocked": "open_mouth_raised_brows",
    "calm": "relaxed_face_open_gaze",
}

_EMOTION_BODY_LANGUAGE: dict[str, str] = {
    "hurt": "shoulders_in_arms_close",
    "anger": "chest_forward_hands_tense",
    "defensive": "crossed_arms_weight_back",
    "vulnerable": "open_palms_slight_bow",
    "confident": "shoulders_back_head_level",
    "shame": "head_down_weight_collapsed",
    "threatened": "slight_step_back_weight_ready",
    "guarded": "neutral_balanced_minimal_movement",
    "hopeful": "open_posture_weight_forward",
    "shocked": "slight_step_back_hand_to_face",
    "calm": "grounded_open_hands_low",
}

_EMOTION_VOICE_PRESSURE: dict[str, str] = {
    "hurt": "low_strained",
    "anger": "sharp_rising",
    "defensive": "clipped_flat",
    "vulnerable": "soft_uneven",
    "confident": "full_steady",
    "shame": "quiet_compressed",
    "threatened": "controlled_but_tight",
    "guarded": "measured_dry",
    "hopeful": "warm_lifting",
    "shocked": "breathy_unstable",
    "calm": "even_warm",
}


def _micro_expression(emotion_state: dict[str, Any], preset: dict[str, Any]) -> str:
    primary = str(emotion_state.get("primary_emotion") or "calm")
    return _EMOTION_MICRO_EXPRESSIONS.get(primary, preset.get("micro_expression_base", "neutral"))


def _body_language(emotion_state: dict[str, Any], preset: dict[str, Any]) -> str:
    primary = str(emotion_state.get("primary_emotion") or "calm")
    return _EMOTION_BODY_LANGUAGE.get(primary, preset.get("body_language_base", "neutral_balanced"))


def _line_delivery(
    acting_profile: dict[str, Any],
    emotion_state: dict[str, Any],
    subtext: str,
    preset: dict[str, Any],
) -> dict[str, str]:
    primary = str(emotion_state.get("primary_emotion") or "calm")
    tension = float(emotion_state.get("tension_level") or 0.0)

    tempo = preset.get("speech_tempo", "moderate")
    if tension > 0.7:
        tempo = "slow_then_sharp"
    elif tension > 0.4:
        tempo = "deliberate"

    pause: str | None = preset.get("pause_style")
    if subtext in {"please_stop_looking_deeper", "i_cannot_face_what_you_are_saying"}:
        pause = "before_key_revelation"
    elif subtext == "hurt_them_before_they_see_me":
        pause = "before_key_accusation"

    voice_pressure = _EMOTION_VOICE_PRESSURE.get(primary, preset.get("voice_pressure_base", "normal"))

    return {
        "tempo": tempo,
        "pause": pause or "measured",
        "voice_pressure": voice_pressure,
    }


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------


class AvatarActingEngine:
    """Orchestrates full acting decision for a given beat + avatar state.

    This is the primary entry point for the director pipeline.
    """

    def __init__(self) -> None:
        self._emotion_engine = AvatarEmotionEngine()
        self._motivation_engine = AvatarMotivationEngine()
        self._subtext_engine = AvatarSubtextEngine()
        self._reaction_engine = AvatarReactionEngine()

    def build(
        self,
        *,
        avatar_profile: dict[str, Any],
        beat: dict[str, Any],
        relationship_state: dict[str, Any] | None = None,
        memory_traces: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Build a complete acting decision payload.

        Parameters
        ----------
        avatar_profile:
            Dict matching ``AvatarActingProfileSchema`` (or acting portion of
            full avatar context).
        beat:
            Story beat dict from StoryBeatEngine.
        relationship_state:
            Optional relationship dict for the primary scene target.
        memory_traces:
            Optional relevant memory traces from AvatarMemoryEngine.

        Returns
        -------
        dict
            Structured acting output matching ``AvatarActingOutput``.
        """
        current_emotion: dict[str, Any] = avatar_profile.get("current_emotional_state") or {
            "primary_emotion": "calm",
            "secondary_emotion": None,
            "tension_level": 0.0,
            "control_level": 0.5,
            "openness_level": 0.5,
            "emotional_mask": None,
            "current_need": None,
            "scene_goal": None,
        }

        # Evolve emotion through beat
        emotion_state = self._emotion_engine.evolve(current_emotion, beat)

        # Resolve motivation / scene goal
        scene_goal = self._motivation_engine.resolve_scene_goal(
            avatar_profile, beat, relationship_state
        )

        # Determine subtext
        spoken_intent = str(beat.get("spoken_intent") or "inform")
        subtext = self._subtext_engine.generate(spoken_intent, emotion_state)

        # Determine reaction under pressure
        pressure_level = float(beat.get("pressure_level") or beat.get("conflict_intensity") or 0.0)
        reaction_pattern = self._reaction_engine.react(avatar_profile, emotion_state, pressure_level)

        # Resolve archetype preset
        preset = _get_preset(avatar_profile)

        return {
            "emotion_state": emotion_state,
            "scene_goal": scene_goal,
            "subtext": subtext,
            "reaction_pattern": reaction_pattern,
            "micro_expression": _micro_expression(emotion_state, preset),
            "body_language": _body_language(emotion_state, preset),
            "line_delivery": _line_delivery(avatar_profile, emotion_state, subtext, preset),
            "memory_activated": bool(memory_traces),
            "memory_count": len(memory_traces) if memory_traces else 0,
        }
