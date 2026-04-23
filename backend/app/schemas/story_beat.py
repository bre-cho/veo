"""story_beat — Pydantic models for story beat structure."""
from __future__ import annotations

import enum

from pydantic import BaseModel


class BeatType(str, enum.Enum):
    hook = "hook"
    setup = "setup"
    escalation = "escalation"
    conflict = "conflict"
    reveal = "reveal"
    climax = "climax"
    resolution = "resolution"
    cta = "cta"
    callback = "callback"


class ConflictType(str, enum.Enum):
    person_vs_person = "person_vs_person"
    person_vs_self = "person_vs_self"
    person_vs_society = "person_vs_society"
    person_vs_nature = "person_vs_nature"
    truth_vs_illusion = "truth_vs_illusion"
    control_vs_freedom = "control_vs_freedom"
    knowledge_vs_ignorance = "knowledge_vs_ignorance"


class StoryBeat(BaseModel):
    beat_index: int
    beat_type: BeatType
    dramatic_intent: str
    emotional_tone: str
    conflict_type: ConflictType | None = None
    duration_weight: float = 1.0
    scene_index: int | None = None
    director_intent: str | None = None
    is_blocked: bool = False
    block_reason: str | None = None
