"""story_beat_engine — expand script/topic into structured story beats."""
from __future__ import annotations

from typing import Any

from app.schemas.story_beat import BeatType, ConflictType, StoryBeat

BEAT_SEQUENCE_DEFAULT = [
    BeatType.hook, BeatType.setup, BeatType.escalation,
    BeatType.conflict, BeatType.reveal, BeatType.climax,
    BeatType.resolution, BeatType.cta,
]

DRAMATIC_INTENT_MAP = {
    BeatType.hook: "grab attention and establish stakes",
    BeatType.setup: "introduce context and character desire",
    BeatType.escalation: "raise tension and complicate the situation",
    BeatType.conflict: "pit opposing forces directly against each other",
    BeatType.reveal: "expose hidden truth that reframes everything",
    BeatType.climax: "reach the highest point of tension",
    BeatType.resolution: "resolve the central conflict",
    BeatType.cta: "inspire the audience to act",
    BeatType.callback: "call back to a previously established promise",
}

EMOTIONAL_TONE_MAP = {
    BeatType.hook: "curiosity",
    BeatType.setup: "anticipation",
    BeatType.escalation: "tension",
    BeatType.conflict: "urgency",
    BeatType.reveal: "surprise",
    BeatType.climax: "intensity",
    BeatType.resolution: "satisfaction",
    BeatType.cta: "motivation",
    BeatType.callback: "resonance",
}


class StoryBeatEngine:
    def expand(self, script_or_topic: str, context: dict[str, Any] | None = None) -> list[StoryBeat]:
        ctx = context or {}
        num_scenes = ctx.get("num_scenes") or len(BEAT_SEQUENCE_DEFAULT)
        beats: list[StoryBeat] = []
        seq = BEAT_SEQUENCE_DEFAULT[:num_scenes]
        for i, beat_type in enumerate(seq):
            conflict_raw = ctx.get("conflict_type")
            conflict_type = None
            if conflict_raw:
                try:
                    conflict_type = ConflictType(conflict_raw)
                except ValueError:
                    pass
            beats.append(StoryBeat(
                beat_index=i,
                beat_type=beat_type,
                dramatic_intent=DRAMATIC_INTENT_MAP.get(beat_type, "advance the story"),
                emotional_tone=EMOTIONAL_TONE_MAP.get(beat_type, "neutral"),
                conflict_type=conflict_type,
                duration_weight=self._duration_weight(beat_type),
                scene_index=i,
                director_intent=f"{beat_type.value}: {DRAMATIC_INTENT_MAP.get(beat_type, '')}",
            ))
        return beats

    def _duration_weight(self, beat_type: BeatType) -> float:
        weights = {BeatType.hook: 0.5, BeatType.climax: 1.5, BeatType.reveal: 1.2, BeatType.cta: 0.5}
        return weights.get(beat_type, 1.0)
