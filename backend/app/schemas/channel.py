from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.scoring import CandidateScore


class ChannelPlanRequest(BaseModel):
    channel_name: str | None = None
    niche: str
    market_code: str | None = None
    goal: str | None = None
    days: int = Field(default=7, ge=1, le=30)
    posts_per_day: int = Field(default=1, ge=1, le=5)
    formats: list[str] | None = None
    project_id: str | None = None
    avatar_id: str | None = None
    product_id: str | None = None
    platform: str | None = None


class ChannelPlanItem(BaseModel):
    day_index: int
    format: str
    title_angle: str
    content_goal: str
    cta_mode: str | None = None
    asset_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChannelPlanResponse(BaseModel):
    plan_id: str | None = None
    series_plan: list[ChannelPlanItem] = Field(default_factory=list)
    publish_queue_count: int
    calendar_summary: dict[str, Any] = Field(default_factory=dict)
    candidates: list[CandidateScore] = Field(default_factory=list)
    winner_candidate_id: str | None = None
