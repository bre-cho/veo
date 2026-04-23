"""brain_intake — request / context schemas for the Brain Layer."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


BrainSourceType = Literal["topic", "script_upload"]
AspectRatio = Literal["9:16", "16:9", "1:1"]
TargetPlatform = Literal["shorts", "tiktok", "reels", "youtube"]

# Re-exported aliases used by older callers
BrainRequestSourceType = BrainSourceType


class BrainContext(BaseModel):
    avatar_id: str | None = None
    market_code: str | None = None
    content_goal: str | None = None
    conversion_mode: str | None = None
    series_id: str | None = None
    episode_index: int | None = None


class BrainIntakeRequest(BaseModel):
    source_type: BrainSourceType
    topic: str | None = None
    script_text: str | None = None
    filename: str | None = None
    aspect_ratio: AspectRatio = "9:16"
    target_platform: TargetPlatform = "shorts"
    style_preset: str | None = None
    avatar_id: str | None = None
    market_code: str | None = None
    content_goal: str | None = None
    conversion_mode: str | None = None
    series_id: str | None = None
    episode_index: int | None = Field(default=None, ge=1)

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    @field_validator("script_text")
    @classmethod
    def validate_script_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class TopicPreviewRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    aspect_ratio: AspectRatio = "9:16"
    target_platform: TargetPlatform = "shorts"
    style_preset: str | None = None
    avatar_id: str | None = None
    market_code: str | None = None
    content_goal: str | None = None
    conversion_mode: str | None = None
    series_id: str | None = None
    episode_index: int | None = Field(default=None, ge=1)
    extra: dict = Field(default_factory=dict)
