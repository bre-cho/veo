from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class BlockingBeatRead(BaseModel):
    character_id: str
    action: str
    spatial_intent: str
    psychological_reason: str
    timing_hint: str = "mid-beat"


class BlockingPlanRead(BaseModel):
    scene_id: Optional[str] = None
    dominant_character_id: Optional[str] = None
    threatened_character_id: Optional[str] = None
    emotional_center_character_id: Optional[str] = None
    spatial_mode: str = Field(default="stable_geometry")
    beats: List[BlockingBeatRead] = Field(default_factory=list)
    blocking_notes: List[str] = Field(default_factory=list)
