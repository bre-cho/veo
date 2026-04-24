from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DialogueSubtextRead(BaseModel):
    id: UUID
    project_id: UUID | None = None
    episode_id: UUID | None = None
    scene_id: UUID
    line_index: int = 0
    speaker_id: UUID
    target_id: UUID | None = None
    literal_intent: str | None = None
    hidden_intent: str | None = None
    psychological_action: str | None = None
    suggested_subtext: str | None = None
    threat_level: float = Field(default=0.0, ge=0.0)
    honesty_level: float = Field(default=0.5, ge=0.0, le=1.0)
    mask_level: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime

    class Config:
        from_attributes = True
