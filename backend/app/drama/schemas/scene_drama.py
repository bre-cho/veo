from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SceneDramaAnalyzeRequest(BaseModel):
    project_id: UUID
    scene_id: UUID
    character_ids: List[UUID] = Field(min_length=2)
    scene_context: Optional[Dict[str, Any]] = None


class SceneIntentRead(BaseModel):
    character_id: str
    outer_goal: Optional[str] = None
    hidden_need: Optional[str] = None
    fear_trigger: Optional[str] = None
    mask_strategy: Optional[str] = None
    likely_scene_intent: str
    pressure_response: Optional[str] = None
    notes: List[str] = []


class SceneTensionRead(BaseModel):
    tension_score: float
    breakdown: Dict[str, float]
    flat_scene: bool


class SceneDramaAnalyzeResponse(BaseModel):
    project_id: str
    scene_id: str
    character_count: int
    intents: List[Dict[str, Any]]
    tension: Dict[str, Any]
    subtext_map: List[Dict[str, Any]]
    power_shift: Dict[str, Any]
    dominant_character_id: Optional[str] = None
    status: str
