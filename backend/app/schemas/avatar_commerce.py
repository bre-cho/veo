from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class CommerceRecommendAvatarRequest(BaseModel):
    content_goal: str
    niche_code: Optional[str] = None
    market_code: Optional[str] = None
    limit: int = 5


class CommerceRecommendAvatarResponse(BaseModel):
    avatars: list[dict[str, Any]]
    content_goal: str


class CommerceRecommendTemplateRequest(BaseModel):
    avatar_id: str
    content_goal: str
    limit: int = 5


class CommerceRecommendTemplateResponse(BaseModel):
    templates: list[dict[str, Any]]
    avatar_id: str
    content_goal: str


class CommerceCTARequest(BaseModel):
    content_goal: str
    conversion_mode: Optional[str] = None


class CommerceCTAResponse(BaseModel):
    cta_text: str
    content_goal: str


class ContentGoalClassifyRequest(BaseModel):
    brief: str


class ContentGoalClassifyResponse(BaseModel):
    content_goal: str
    confidence: float


class ProductTemplateRouterRequest(BaseModel):
    product_brief: str
    market_code: Optional[str] = None


class ProductTemplateRouterResponse(BaseModel):
    template_family_id: Optional[str] = None
    template_name: Optional[str] = None
    content_goal: str
    rationale: str


class CommerceOptimizeRequest(BaseModel):
    niche: str
    goal: Optional[str] = None
    days: int = 7
    posts_per_day: int = 1
    market_code: Optional[str] = None
    platform: Optional[str] = None
    formats: Optional[list[str]] = None
    budget_constraint: Optional[float] = None
    objectives: Optional[dict[str, float]] = None
    channel_name: Optional[str] = None
    avatar_id: Optional[str] = None
    product_id: Optional[str] = None
    project_id: Optional[str] = None


class CommerceOptimizeResponse(BaseModel):
    plan_id: Optional[str] = None
    series_plan: list[Any] = []
    publish_queue_count: int
    calendar_summary: dict[str, Any] = {}
    candidates: list[Any] = []
    winner_candidate_id: Optional[str] = None
