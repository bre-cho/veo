from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DramaMemoryTraceBase(BaseModel):
    project_id: UUID | None = None
    episode_id: UUID | None = None
    character_id: UUID
    related_character_id: UUID | None = None
    source_scene_id: UUID | None = None
    event_type: str
    meaning_label: str | None = None
    recall_trigger: str | None = None
    notes: str | None = None
    emotional_weight: float = Field(default=0.0, ge=0.0)
    trust_impact: float = 0.0
    shame_impact: float = 0.0
    fear_impact: float = 0.0
    dominance_impact: float = 0.0
    persistence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    decay_rate: float = Field(default=0.05, ge=0.0, le=1.0)


class DramaMemoryTraceCreate(DramaMemoryTraceBase):
    pass


class DramaMemoryTraceRead(DramaMemoryTraceBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
