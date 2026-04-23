"""storyboard_frame — Pydantic models for storyboard frame composition."""
from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field


class FrameCompositionRule(str, enum.Enum):
    rule_of_thirds = "rule_of_thirds"
    centered = "centered"
    golden_ratio = "golden_ratio"
    symmetry = "symmetry"
    leading_lines = "leading_lines"
    frame_in_frame = "frame_in_frame"
    negative_space = "negative_space"


class StoryboardFrame(BaseModel):
    frame_index: int
    scene_index: int
    beat_index: int | None = None
    shot_type: str
    movement: str
    composition_rule: FrameCompositionRule = FrameCompositionRule.rule_of_thirds
    lighting_plan: dict[str, Any] = Field(default_factory=dict)
    blocking_notes: str | None = None
    performance_notes: str | None = None
    director_intent: str | None = None
    conflict_core: str | None = None
    shot_purpose: str | None = None
