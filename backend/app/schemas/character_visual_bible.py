"""character_visual_bible — Pydantic model for character visual bible."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.director_language import AvatarArchetype


class CharacterVisualBible(BaseModel):
    avatar_id: str
    archetype: AvatarArchetype
    silhouette: str | None = None
    face_geometry: str | None = None
    posture: str | None = None
    color_palette: list[str] = Field(default_factory=list)
    prop_signature: list[str] = Field(default_factory=list)
    speaking_rhythm: str | None = None
    gaze_pattern: str | None = None
    emotional_range: str | None = None
    default_energy: str | None = None
    preferred_shots: list[str] = Field(default_factory=list)
    forbidden_shots: list[str] = Field(default_factory=list)
    lighting_bias: dict[str, Any] = Field(default_factory=dict)
    core_desire: str | None = None
    core_fear: str | None = None
    contradiction: str | None = None
