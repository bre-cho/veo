from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SceneDramaStateBase(BaseModel):
    project_id: UUID | None = None
    episode_id: UUID | None = None
    scene_id: UUID
    scene_goal: str | None = None
    visible_conflict: str | None = None
    hidden_conflict: str | None = None
    scene_temperature: float = 0.0
    pressure_level: float = 0.0
    dominant_character_id: UUID | None = None
    emotional_center_character_id: UUID | None = None
    threatened_character_id: UUID | None = None
    turning_point: str | None = None
    outcome_type: str | None = None
    power_shift_delta: float = 0.0
    trust_shift_delta: float = 0.0
    exposure_shift_delta: float = 0.0
    dependency_shift_delta: float = 0.0
    analysis_payload: dict | None = None
    continuity_payload: dict | None = None
    compile_payload: dict | None = None
    notes: str | None = None


class SceneDramaStateRead(SceneDramaStateBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ArcProgressBase(BaseModel):
    project_id: UUID | None = None
    episode_id: UUID | None = None
    character_id: UUID
    arc_name: str
    arc_stage: str = "mask_stable"
    false_belief: str | None = None
    pressure_index: float = Field(default=0.0, ge=0.0, le=1.0)
    transformation_index: float = Field(default=0.0, ge=0.0, le=1.0)
    collapse_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    mask_break_level: float = Field(default=0.0, ge=0.0, le=1.0)
    truth_acceptance_level: float = Field(default=0.0, ge=0.0, le=1.0)
    relation_entanglement_index: float = Field(default=0.0, ge=0.0, le=1.0)
    latest_scene_id: UUID | None = None
    notes: str | None = None


class ArcProgressRead(ArcProgressBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
