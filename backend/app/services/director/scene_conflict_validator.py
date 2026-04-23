"""scene_conflict_validator — validate story beats and block problematic ones."""
from __future__ import annotations

from typing import Any

from app.schemas.story_beat import StoryBeat, BeatType

BLOCKED_SEQUENCES = {
    (BeatType.climax, BeatType.hook),  # climax before hook makes no sense
}


class SceneConflictValidator:
    def validate(self, beat: StoryBeat) -> str:
        """Returns 'OK' or 'BLOCK'."""
        if beat.is_blocked:
            return "BLOCK"
        # beats without dramatic intent are weak but not blocked
        if not beat.dramatic_intent:
            return "WARN"
        return "OK"

    def validate_sequence(self, beats: list[StoryBeat]) -> list[StoryBeat]:
        """Mark beats as blocked if they violate sequence rules."""
        validated = []
        prev_type = None
        for beat in beats:
            if prev_type and (prev_type, beat.beat_type) in BLOCKED_SEQUENCES:
                beat = beat.model_copy(update={"is_blocked": True, "block_reason": f"invalid sequence after {prev_type}"})
            validated.append(beat)
            prev_type = beat.beat_type
        return validated
