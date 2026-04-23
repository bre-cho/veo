"""performance_blocking_engine — generate character blocking + performance notes."""
from __future__ import annotations

from typing import Any

from app.schemas.story_beat import StoryBeat, BeatType
from app.schemas.director_language import AvatarArchetype

ARCHETYPE_PERFORMANCE: dict[str, dict[str, Any]] = {
    AvatarArchetype.mentor.value: {"speaking_rhythm": "slow_deliberate", "gaze_pattern": "direct_sustained", "micro_expression": "calm_knowing", "body_action": "minimal_gestures", "pause_pattern": "long_pauses"},
    AvatarArchetype.villain.value: {"speaking_rhythm": "controlled_precise", "gaze_pattern": "oblique_then_direct", "micro_expression": "micro_smile", "body_action": "slow_dominant_movement", "pause_pattern": "strategic_silence"},
    AvatarArchetype.truth_revealer.value: {"speaking_rhythm": "building_crescendo", "gaze_pattern": "intense_forward", "micro_expression": "restrained_urgency", "body_action": "lean_forward", "pause_pattern": "pre_reveal_pause"},
    AvatarArchetype.authority.value: {"speaking_rhythm": "steady_measured", "gaze_pattern": "straight_ahead", "micro_expression": "neutral_commanding", "body_action": "still_upright", "pause_pattern": "minimal"},
    AvatarArchetype.rebel.value: {"speaking_rhythm": "fast_rhythmic", "gaze_pattern": "scanning_then_locking", "micro_expression": "fierce_conviction", "body_action": "dynamic_movement", "pause_pattern": "beat_pause"},
    AvatarArchetype.manipulator.value: {"speaking_rhythm": "variable_deceptive", "gaze_pattern": "side_glance", "micro_expression": "false_warmth", "body_action": "mirroring", "pause_pattern": "calculated"},
    AvatarArchetype.observer.value: {"speaking_rhythm": "measured_neutral", "gaze_pattern": "watchful_peripheral", "micro_expression": "subtle_reaction", "body_action": "restrained", "pause_pattern": "observer_beat"},
}

BEAT_PERFORMANCE_OVERRIDE: dict[BeatType, dict[str, Any]] = {
    BeatType.climax: {"speaking_rhythm": "peak_intensity", "micro_expression": "raw_emotion"},
    BeatType.reveal: {"pause_pattern": "pre_reveal_pause", "body_action": "stillness_before_action"},
    BeatType.hook: {"gaze_pattern": "direct_lens", "body_action": "establish_presence"},
    BeatType.cta: {"gaze_pattern": "direct_lens", "speaking_rhythm": "energetic_direct"},
}


class PerformanceBlockingEngine:
    def build(self, beat: StoryBeat, character_state: dict[str, Any] | None = None) -> dict[str, Any]:
        state = character_state or {}
        archetype = state.get("archetype") or AvatarArchetype.observer.value
        base = dict(ARCHETYPE_PERFORMANCE.get(archetype, ARCHETYPE_PERFORMANCE[AvatarArchetype.observer.value]))
        override = BEAT_PERFORMANCE_OVERRIDE.get(beat.beat_type) or {}
        base.update(override)
        return {
            "blocking": base,
            "archetype": archetype,
            "beat_type": beat.beat_type.value,
            "emotional_tone": beat.emotional_tone,
            "arc_stage": state.get("arc_stage"),
        }
