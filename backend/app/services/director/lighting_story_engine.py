"""lighting_story_engine — map story beats to cinematic lighting plans."""
from __future__ import annotations

from typing import Any

from app.schemas.story_beat import StoryBeat, BeatType
from app.schemas.director_language import DirectorLightingPlan, LightingKey, LightingColor, AvatarArchetype

ARCHETYPE_LIGHTING: dict[str, dict[str, Any]] = {
    AvatarArchetype.mentor.value: {"key_light": LightingKey.soft, "contrast": "low", "color": LightingColor.warm, "fill_ratio": 0.7},
    AvatarArchetype.villain.value: {"key_light": LightingKey.hard_side, "contrast": "high", "color": LightingColor.cold_green, "fill_ratio": 0.2},
    AvatarArchetype.truth_revealer.value: {"key_light": LightingKey.top_light, "contrast": "medium", "color": LightingColor.neutral, "fill_ratio": 0.5},
    AvatarArchetype.authority.value: {"key_light": LightingKey.hard, "contrast": "medium", "color": LightingColor.cold, "fill_ratio": 0.4},
    AvatarArchetype.rebel.value: {"key_light": LightingKey.rim, "contrast": "high", "color": LightingColor.amber, "fill_ratio": 0.3},
    AvatarArchetype.manipulator.value: {"key_light": LightingKey.practical, "contrast": "medium", "color": LightingColor.cold_green, "fill_ratio": 0.35},
    AvatarArchetype.observer.value: {"key_light": LightingKey.soft, "contrast": "low", "color": LightingColor.neutral, "fill_ratio": 0.6},
}

BEAT_LIGHTING_OVERRIDE: dict[BeatType, dict[str, Any]] = {
    BeatType.climax: {"contrast": "high", "fill_ratio": 0.2},
    BeatType.reveal: {"key_light": LightingKey.top_light, "contrast": "medium"},
    BeatType.resolution: {"contrast": "low", "fill_ratio": 0.7, "color": LightingColor.warm},
    BeatType.hook: {"contrast": "high"},
}


class LightingStoryEngine:
    def plan(self, beat: StoryBeat, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = context or {}
        archetype = ctx.get("archetype") or AvatarArchetype.observer.value
        base = dict(ARCHETYPE_LIGHTING.get(archetype, ARCHETYPE_LIGHTING[AvatarArchetype.observer.value]))
        override = BEAT_LIGHTING_OVERRIDE.get(beat.beat_type) or {}
        base.update(override)
        plan = DirectorLightingPlan(**base)
        return {
            "lighting_plan": plan.model_dump(),
            "archetype": archetype,
            "beat_type": beat.beat_type.value,
            "lighting_intent": f"{archetype} character in {beat.beat_type.value} beat",
        }
