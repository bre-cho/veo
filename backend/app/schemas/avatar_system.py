"""avatar_system — Pydantic schemas for the Avatar System layer.

Classes
-------
AvatarVoiceProfile       — voice provider + delivery parameters
AvatarIdentityProfile    — complete avatar persona + context affinity
AvatarContinuityState    — per-series episode continuity snapshot
AvatarSelectionResult    — output of AvatarIdentityEngine.select_avatar()
AvatarPerformanceScore   — computed from publish metrics
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AvatarVoiceProfile(BaseModel):
    provider: str | None = None
    voice_id: str | None = None
    delivery_style: str | None = None
    speaking_rate: float = 1.0
    pitch: float = 1.0
    intensity: float = 1.0


class AvatarIdentityProfile(BaseModel):
    avatar_id: str
    display_name: str
    persona: str
    narrative_role: str
    tone: str
    visual_style: str
    belief_system: str | None = None
    market_code: str | None = None
    content_goals: list[str] = Field(default_factory=list)
    topic_classes: list[str] = Field(default_factory=list)
    reference_image_urls: list[str] = Field(default_factory=list)
    default_expression: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AvatarContinuityState(BaseModel):
    avatar_id: str
    series_id: str | None = None
    episode_index: int | None = None
    narrative_arc_state: str | None = None
    emotion_curve: str | None = None
    callback_targets: list[str] = Field(default_factory=list)
    continuity_constraints: dict[str, Any] = Field(default_factory=dict)


class AvatarSelectionResult(BaseModel):
    avatar_id: str
    score: float
    reasons: list[str] = Field(default_factory=list)
    identity: dict[str, Any] = Field(default_factory=dict)
    voice: dict[str, Any] = Field(default_factory=dict)


class AvatarPerformanceScore(BaseModel):
    avatar_id: str
    market_code: str | None = None
    content_goal: str | None = None
    topic_class: str | None = None
    retention_score: float = 0.0
    engagement_score: float = 0.0
    series_follow_score: float = 0.0
    total_score: float = 0.0
