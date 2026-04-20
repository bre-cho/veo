from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class GenerateReviewVideoRequest(BaseModel):
    product_name: str = Field(..., min_length=1)
    product_features: list[str] = Field(..., min_length=1)
    target_audience: str = Field(..., min_length=1)
    conversion_mode: Optional[str] = None
    market_code: Optional[str] = None
    avatar_id: Optional[str] = None
    aspect_ratio: str = "9:16"
    target_platform: str = "shorts"


class ReviewVideoSceneOut(BaseModel):
    scene_index: int
    scene_role: str
    title: str
    script_text: str
    visual_prompt: str
    target_duration_sec: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversionScoreResult(BaseModel):
    conversion_score: float
    details: dict[str, Any] = Field(default_factory=dict)


class GenerateReviewVideoResponse(BaseModel):
    product_name: str
    target_audience: str
    content_goal: str
    conversion_mode: Optional[str] = None
    hook: str
    body: str
    cta: str
    scenes: list[ReviewVideoSceneOut]
    conversion_score_result: ConversionScoreResult
    preview_payload: dict[str, Any]
