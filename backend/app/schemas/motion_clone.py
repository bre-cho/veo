from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MotionCloneRequest(BaseModel):
    reference_video_url: str | None = None
    reference_motion_text: str | None = None
    beat_profile: dict[str, Any] | None = None
    avatar_id: str | None = None
    market_code: str | None = None


class MotionCloneResponse(BaseModel):
    motion_plan: dict[str, Any] = Field(default_factory=dict)
    beat_sync_map: list[dict[str, Any]] = Field(default_factory=list)
    animation_guidance_payload: dict[str, Any] = Field(default_factory=dict)
