from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RelationshipCreate(BaseModel):
    project_id: UUID
    source_character_id: UUID
    target_character_id: UUID
    relation_type: str = Field(..., min_length=1, max_length=64)

    intimacy_level: float = Field(0.0, ge=0.0, le=1.0)
    trust_level: float = Field(0.0, ge=0.0, le=1.0)
    dependence_level: float = Field(0.0, ge=0.0, le=1.0)
    fear_level: float = Field(0.0, ge=0.0, le=1.0)
    resentment_level: float = Field(0.0, ge=0.0, le=1.0)
    attraction_level: float = Field(0.0, ge=0.0, le=1.0)
    rivalry_level: float = Field(0.0, ge=0.0, le=1.0)
    dominance_source_over_target: float = Field(0.0, ge=0.0, le=1.0)
    perceived_loyalty: float = Field(0.0, ge=0.0, le=1.0)
    hidden_agenda_score: float = Field(0.0, ge=0.0, le=1.0)
    recent_betrayal_score: float = Field(0.0, ge=0.0, le=1.0)
    unresolved_tension_score: float = Field(0.0, ge=0.0, le=1.0)
    status: str = Field("active", min_length=1, max_length=32)
    last_interaction_scene_id: Optional[str] = Field(None, max_length=128)


class RelationshipUpdate(BaseModel):
    relation_type: Optional[str] = Field(None, min_length=1, max_length=64)
    intimacy_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    trust_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    dependence_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    fear_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    resentment_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    attraction_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    rivalry_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    dominance_source_over_target: Optional[float] = Field(None, ge=0.0, le=1.0)
    perceived_loyalty: Optional[float] = Field(None, ge=0.0, le=1.0)
    hidden_agenda_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    recent_betrayal_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    unresolved_tension_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    status: Optional[str] = Field(None, min_length=1, max_length=32)
    last_interaction_scene_id: Optional[str] = Field(None, max_length=128)


class RelationshipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    source_character_id: UUID
    target_character_id: UUID
    relation_type: str
    intimacy_level: float
    trust_level: float
    dependence_level: float
    fear_level: float
    resentment_level: float
    attraction_level: float
    rivalry_level: float
    dominance_source_over_target: float
    perceived_loyalty: float
    hidden_agenda_score: float
    recent_betrayal_score: float
    unresolved_tension_score: float
    status: str
    last_interaction_scene_id: Optional[str] = None
    updated_at: datetime
