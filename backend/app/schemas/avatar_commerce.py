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
