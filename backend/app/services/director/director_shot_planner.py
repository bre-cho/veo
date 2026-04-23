"""director_shot_planner — plan shot grammar for each story beat."""
from __future__ import annotations

from typing import Any

from app.schemas.story_beat import StoryBeat, BeatType
from app.schemas.director_language import DirectorShotGrammar, ShotType, CameraMovement

SHOT_PLAN_MAP: dict[BeatType, dict[str, Any]] = {
    BeatType.hook: {"shot_type": ShotType.extreme_close, "movement": CameraMovement.push_in, "framing": "tight_face", "lens_feel": "compressed"},
    BeatType.setup: {"shot_type": ShotType.medium, "movement": CameraMovement.static, "framing": "balanced", "lens_feel": "normal"},
    BeatType.escalation: {"shot_type": ShotType.medium_close, "movement": CameraMovement.handheld, "framing": "unstable", "lens_feel": "normal"},
    BeatType.conflict: {"shot_type": ShotType.two_shot, "movement": CameraMovement.static, "framing": "confrontation", "lens_feel": "normal"},
    BeatType.reveal: {"shot_type": ShotType.close, "movement": CameraMovement.pull_out, "framing": "reveal_space", "lens_feel": "wide"},
    BeatType.climax: {"shot_type": ShotType.extreme_close, "movement": CameraMovement.push_in, "framing": "maximum_tension", "lens_feel": "compressed"},
    BeatType.resolution: {"shot_type": ShotType.wide, "movement": CameraMovement.pull_out, "framing": "release_space", "lens_feel": "wide"},
    BeatType.cta: {"shot_type": ShotType.medium_close, "movement": CameraMovement.static, "framing": "direct_address", "lens_feel": "normal"},
    BeatType.callback: {"shot_type": ShotType.over_shoulder, "movement": CameraMovement.static, "framing": "intimate", "lens_feel": "normal"},
}

SHOT_PURPOSE_MAP: dict[BeatType, str] = {
    BeatType.hook: "establish immediate emotional hook",
    BeatType.setup: "orient viewer in the world",
    BeatType.escalation: "create physical tension",
    BeatType.conflict: "show power dynamic between forces",
    BeatType.reveal: "reframe the entire story",
    BeatType.climax: "maximize emotional impact",
    BeatType.resolution: "release built tension",
    BeatType.cta: "direct viewer to action",
    BeatType.callback: "reward audience memory",
}


class DirectorShotPlanner:
    def plan(self, beat: StoryBeat, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = context or {}
        defaults = SHOT_PLAN_MAP.get(beat.beat_type, SHOT_PLAN_MAP[BeatType.setup])
        grammar = DirectorShotGrammar(**defaults)
        shot_purpose = SHOT_PURPOSE_MAP.get(beat.beat_type, "advance the narrative")
        # Avatar visual bible override
        visual_bible = ctx.get("character_visual_bible") or {}
        preferred = visual_bible.get("preferred_shots") or []
        forbidden = visual_bible.get("forbidden_shots") or []
        if grammar.shot_type.value in forbidden and preferred:
            grammar = grammar.model_copy(update={"shot_type": ShotType(preferred[0])})
        return {
            "shot_grammar": grammar.model_dump(),
            "shot_purpose": shot_purpose,
            "beat_type": beat.beat_type.value,
            "dramatic_intent": beat.dramatic_intent,
        }
