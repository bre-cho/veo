from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PowerShiftRead(BaseModel):
    id: UUID
    project_id: UUID | None = None
    episode_id: UUID | None = None
    scene_id: UUID
    from_character_id: UUID
    to_character_id: UUID
    trigger_event: str | None = None
    social_delta: float = 0.0
    emotional_delta: float = 0.0
    informational_delta: float = 0.0
    moral_delta: float = 0.0
    spatial_delta: float = 0.0
    narrative_control_delta: float = 0.0
    created_at: datetime

    class Config:
        from_attributes = True
