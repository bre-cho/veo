"""director_language — Pydantic models for director intent and shot grammar."""
from __future__ import annotations

import enum

from pydantic import BaseModel


class ShotType(str, enum.Enum):
    extreme_wide = "extreme_wide"
    wide = "wide"
    medium = "medium"
    medium_close = "medium_close"
    close = "close"
    extreme_close = "extreme_close"
    over_shoulder = "over_shoulder"
    two_shot = "two_shot"
    pov = "pov"
    insert = "insert"


class CameraMovement(str, enum.Enum):
    static = "static"
    push_in = "push_in"
    pull_out = "pull_out"
    pan_left = "pan_left"
    pan_right = "pan_right"
    tilt_up = "tilt_up"
    tilt_down = "tilt_down"
    tracking = "tracking"
    handheld = "handheld"
    crane = "crane"


class LightingKey(str, enum.Enum):
    soft = "soft"
    hard = "hard"
    hard_side = "hard_side"
    top_light = "top_light"
    under_light = "under_light"
    rim = "rim"
    practical = "practical"


class LightingColor(str, enum.Enum):
    warm = "warm"
    cold = "cold"
    neutral = "neutral"
    cold_green = "cold_green"
    amber = "amber"
    blue = "blue"


class AvatarArchetype(str, enum.Enum):
    mentor = "mentor"
    rebel = "rebel"
    observer = "observer"
    villain = "villain"
    truth_revealer = "truth_revealer"
    authority = "authority"
    manipulator = "manipulator"


class DirectorShotGrammar(BaseModel):
    shot_type: ShotType
    movement: CameraMovement
    framing: str
    lens_feel: str = "normal"


class DirectorLightingPlan(BaseModel):
    key_light: LightingKey
    contrast: str = "medium"
    color: LightingColor = LightingColor.neutral
    fill_ratio: float = 0.5


class DirectorIntent(BaseModel):
    dramatic_intent: str
    emotional_arc: str
    conflict_type: str | None = None
    shot_purpose: str
    shot_grammar: DirectorShotGrammar | None = None
    lighting_plan: DirectorLightingPlan | None = None
