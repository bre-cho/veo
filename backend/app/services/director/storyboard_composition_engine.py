"""storyboard_composition_engine — compose storyboard frames from beats + shot plans."""
from __future__ import annotations

from typing import Any

from app.schemas.story_beat import StoryBeat, BeatType
from app.schemas.storyboard_frame import StoryboardFrame, FrameCompositionRule

COMPOSITION_MAP: dict[BeatType, FrameCompositionRule] = {
    BeatType.hook: FrameCompositionRule.rule_of_thirds,
    BeatType.setup: FrameCompositionRule.golden_ratio,
    BeatType.escalation: FrameCompositionRule.leading_lines,
    BeatType.conflict: FrameCompositionRule.symmetry,
    BeatType.reveal: FrameCompositionRule.negative_space,
    BeatType.climax: FrameCompositionRule.centered,
    BeatType.resolution: FrameCompositionRule.golden_ratio,
    BeatType.cta: FrameCompositionRule.centered,
    BeatType.callback: FrameCompositionRule.frame_in_frame,
}


class StoryboardCompositionEngine:
    def compose(
        self,
        beat: StoryBeat,
        shot_plan: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> StoryboardFrame:
        ctx = context or {}
        grammar = shot_plan.get("shot_grammar") or {}
        lighting = ctx.get("lighting_plan") or {}
        blocking = ctx.get("blocking") or {}
        composition_rule = COMPOSITION_MAP.get(beat.beat_type, FrameCompositionRule.rule_of_thirds)
        return StoryboardFrame(
            frame_index=beat.beat_index,
            scene_index=beat.scene_index if beat.scene_index is not None else beat.beat_index,
            beat_index=beat.beat_index,
            shot_type=grammar.get("shot_type", "medium"),
            movement=grammar.get("movement", "static"),
            composition_rule=composition_rule,
            lighting_plan=lighting,
            blocking_notes=blocking.get("body_action"),
            performance_notes=blocking.get("micro_expression"),
            director_intent=beat.director_intent,
            conflict_core=beat.conflict_type.value if beat.conflict_type else None,
            shot_purpose=shot_plan.get("shot_purpose"),
        )
