from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TrendImageRequest(BaseModel):
    topic: str
    niche: str | None = None
    market_code: str | None = None
    content_goal: str | None = None
    style_preset: str | None = None
    count: int = Field(default=4, ge=1, le=12)


class TrendImageConcept(BaseModel):
    concept_id: str
    title: str
    prompt_text: str
    style_label: str | None = None
    trend_score: float
    thumbnail_bias: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrendImageResponse(BaseModel):
    concepts: list[TrendImageConcept] = Field(default_factory=list)
    recommended_winner_id: str | None = None
