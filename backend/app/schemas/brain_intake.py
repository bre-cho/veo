"""brain_intake — request / context schemas for the Brain Layer."""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


BrainRequestSourceType = Literal["topic", "script_upload"]


class BrainContext(BaseModel):
    avatar_id: str | None = None
    market_code: str | None = None
    content_goal: str | None = None
    conversion_mode: str | None = None
    series_id: str | None = None
    episode_index: int | None = None


class BrainIntakeRequest(BaseModel):
    source_type: BrainRequestSourceType
    topic: str | None = None
    script_text: str | None = None
    filename: str | None = None
    aspect_ratio: Literal["9:16", "16:9", "1:1"] = "9:16"
    target_platform: Literal["shorts", "tiktok", "reels", "youtube"] = "shorts"
    style_preset: str | None = None
    avatar_id: str | None = None
    market_code: str | None = None
    content_goal: str | None = None
    conversion_mode: str | None = None
    series_id: str | None = None
    episode_index: int | None = None


class TopicPreviewRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    aspect_ratio: Literal["9:16", "16:9", "1:1"] = "9:16"
    target_platform: Literal["shorts", "tiktok", "reels", "youtube"] = "shorts"
    style_preset: str | None = None
    avatar_id: str | None = None
    market_code: str | None = None
    content_goal: str | None = None
    conversion_mode: str | None = None
    series_id: str | None = None
    episode_index: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
