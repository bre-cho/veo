from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CharacterCreate(BaseModel):
    project_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    archetype: str = Field(..., min_length=1, max_length=100)

    public_persona: Optional[str] = None
    private_self: Optional[str] = None
    outer_goal: Optional[str] = None
    hidden_need: Optional[str] = None
    core_wound: Optional[str] = None
    dominant_fear: Optional[str] = None
    mask_strategy: Optional[str] = None
    pressure_response: Optional[str] = None

    speech_pattern: Optional[dict[str, Any]] = None
    movement_pattern: Optional[dict[str, Any]] = None
    gaze_pattern: Optional[dict[str, Any]] = None
    acting_preset_seed: Optional[dict[str, Any]] = None

    status_default: float = Field(0.5, ge=0.0, le=1.0)
    dominance_baseline: float = Field(0.5, ge=0.0, le=1.0)
    trust_baseline: float = Field(0.5, ge=0.0, le=1.0)
    openness_baseline: float = Field(0.5, ge=0.0, le=1.0)
    volatility_baseline: float = Field(0.5, ge=0.0, le=1.0)
    tags: Optional[list[str]] = None


class CharacterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    archetype: Optional[str] = Field(None, min_length=1, max_length=100)
    public_persona: Optional[str] = None
    private_self: Optional[str] = None
    outer_goal: Optional[str] = None
    hidden_need: Optional[str] = None
    core_wound: Optional[str] = None
    dominant_fear: Optional[str] = None
    mask_strategy: Optional[str] = None
    pressure_response: Optional[str] = None
    speech_pattern: Optional[dict[str, Any]] = None
    movement_pattern: Optional[dict[str, Any]] = None
    gaze_pattern: Optional[dict[str, Any]] = None
    acting_preset_seed: Optional[dict[str, Any]] = None
    status_default: Optional[float] = Field(None, ge=0.0, le=1.0)
    dominance_baseline: Optional[float] = Field(None, ge=0.0, le=1.0)
    trust_baseline: Optional[float] = Field(None, ge=0.0, le=1.0)
    openness_baseline: Optional[float] = Field(None, ge=0.0, le=1.0)
    volatility_baseline: Optional[float] = Field(None, ge=0.0, le=1.0)
    tags: Optional[list[str]] = None


class CharacterStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    character_id: UUID
    scene_id: Optional[str] = None
    emotional_valence: float
    arousal: float
    control_level: float
    dominance_level: float
    vulnerability_level: float
    trust_level: float
    shame_level: float
    anger_level: float
    fear_level: float
    desire_level: float
    openness_level: float
    mask_strength: float
    internal_conflict_level: float
    goal_pressure_level: float
    current_subtext: Optional[str] = None
    current_secret_load: Optional[str] = None
    current_power_position: str
    update_reason: Optional[str] = None
    created_at: datetime


class CharacterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    archetype: str
    public_persona: Optional[str] = None
    private_self: Optional[str] = None
    outer_goal: Optional[str] = None
    hidden_need: Optional[str] = None
    core_wound: Optional[str] = None
    dominant_fear: Optional[str] = None
    mask_strategy: Optional[str] = None
    pressure_response: Optional[str] = None
    speech_pattern: Optional[dict[str, Any]] = None
    movement_pattern: Optional[dict[str, Any]] = None
    gaze_pattern: Optional[dict[str, Any]] = None
    acting_preset_seed: Optional[dict[str, Any]] = None
    status_default: float
    dominance_baseline: float
    trust_baseline: float
    openness_baseline: float
    volatility_baseline: float
    tags: Optional[list[str]] = None
    created_at: datetime
    updated_at: datetime


class CharacterWithStateRead(BaseModel):
    character: CharacterRead
    latest_state: Optional[CharacterStateRead] = None
