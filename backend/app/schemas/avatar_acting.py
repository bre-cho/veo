"""avatar_acting — Pydantic schemas for the Avatar Acting Model.

Classes
-------
AvatarActingProfileSchema     — immutable character/performance spec
AvatarEmotionalStateSchema    — current emotional state snapshot
AvatarRelationshipStateSchema — avatar ↔ entity relationship levels
AvatarMemoryTraceSchema       — single episodic memory record
AvatarActingOutput            — full acting decision returned by AvatarActingEngine
AvatarActingScorecardSchema   — post-render acting quality scorecard
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AvatarActingProfileSchema(BaseModel):
    avatar_id: str
    archetype: str = "observer"
    temperament: str = "calm"
    defense_mechanism: str = "withdrawal"
    vulnerability_axis: str = "shame"
    desire_axis: str = "control"
    baseline_energy: str = "medium"
    speech_tempo: str = "moderate"
    pause_style: str = "measured"
    gaze_style: str = "direct"
    touch_boundary: str = "distant"
    reaction_style: str = "controlled"
    shot_grammar: dict[str, Any] = Field(default_factory=dict)
    lighting_signature: dict[str, Any] = Field(default_factory=dict)
    preferred_shots: list[str] = Field(default_factory=list)
    forbidden_shots: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AvatarEmotionalStateSchema(BaseModel):
    primary_emotion: str = "calm"
    secondary_emotion: str | None = None
    tension_level: float = 0.0
    control_level: float = 0.5
    openness_level: float = 0.5
    emotional_mask: str | None = None
    current_need: str | None = None
    scene_goal: str | None = None


class AvatarRelationshipStateSchema(BaseModel):
    avatar_id: str
    target_entity_id: str
    trust_level: float = 0.5
    fear_level: float = 0.0
    dominance_level: float = 0.5
    resentment_level: float = 0.0
    attraction_level: float = 0.0
    dependency_level: float = 0.0


class AvatarMemoryTraceSchema(BaseModel):
    avatar_id: str
    memory_type: str = "event"
    trigger: str
    emotional_weight: float = 0.5
    narrative_summary: str
    continuity_tag: str | None = None
    source_scene_index: int | None = None
    source_series_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LineDeliverySchema(BaseModel):
    tempo: str = "moderate"
    pause: str | None = None
    voice_pressure: str = "normal"


class AvatarActingOutput(BaseModel):
    """Structured acting decision output consumed by render / shot planner."""

    emotion_state: AvatarEmotionalStateSchema
    scene_goal: str
    subtext: str
    reaction_pattern: str
    micro_expression: str
    body_language: str
    line_delivery: LineDeliverySchema


class AvatarActingScorecardSchema(BaseModel):
    """Post-render acting quality scorecard."""

    emotional_clarity: float = 0.0
    subtext_readability: float = 0.0
    behavior_consistency: float = 0.0
    reaction_truthfulness: float = 0.0
    character_continuity: float = 0.0
    total_acting_score: float = 0.0
