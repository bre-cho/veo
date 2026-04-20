from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Storyboard schemas
# ---------------------------------------------------------------------------


class SceneBeatOut(BaseModel):
    scene_index: int
    scene_goal: str
    visual_type: str
    emotion: str
    cta_flag: bool
    script_text: str
    title: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class StoryboardGenerateRequest(BaseModel):
    script: str = Field(..., min_length=1)
    max_scenes: int = Field(default=10, ge=1, le=20)


class StoryboardGenerateResponse(BaseModel):
    scene_count: int
    scenes: list[SceneBeatOut]


# ---------------------------------------------------------------------------
# Advanced commerce schemas
# ---------------------------------------------------------------------------


class GenerateCTARequest(BaseModel):
    intent: str = Field(..., description="urgency | discount | social_proof | soft | default")
    product_name: str = Field(..., min_length=1)
    target_audience: str = Field(..., min_length=1)
    discount: str = "20% off"
    deadline: str = "midnight tonight"
    all_variants: bool = False


class GenerateCTAResponse(BaseModel):
    intent: str
    cta_text: str
    variants: list[str] = Field(default_factory=list)


class GenerateHookRequest(BaseModel):
    template_type: str = Field(..., description="review | testimonial | comparison | viral | educational")
    product_name: str = Field(..., min_length=1)
    pain_hint: str = Field(..., min_length=1)
    target_audience: str = Field(..., min_length=1)
    stat: str = "9 out of 10"
    all_variants: bool = False


class GenerateHookResponse(BaseModel):
    template_type: str
    hook_text: str
    variants: list[str] = Field(default_factory=list)


class GenerateTestimonialVideoRequest(BaseModel):
    product_name: str = Field(..., min_length=1)
    product_features: list[str] = Field(..., min_length=1)
    target_audience: str = Field(..., min_length=1)
    conversion_mode: Optional[str] = None
    market_code: Optional[str] = None
    avatar_id: Optional[str] = None
    aspect_ratio: str = "9:16"
    target_platform: str = "shorts"
    hook_variant: int = 0


class GenerateComparisonVideoRequest(BaseModel):
    product_name: str = Field(..., min_length=1)
    competitor_name: str = Field(..., min_length=1)
    product_features: list[str] = Field(..., min_length=1)
    target_audience: str = Field(..., min_length=1)
    conversion_mode: Optional[str] = None
    market_code: Optional[str] = None
    avatar_id: Optional[str] = None
    aspect_ratio: str = "9:16"
    target_platform: str = "shorts"
    hook_variant: int = 0


# ---------------------------------------------------------------------------
# Template intelligence schemas
# ---------------------------------------------------------------------------


class TemplateIntelligenceRequest(BaseModel):
    content_goal: str = Field(..., min_length=1)
    market_code: Optional[str] = None


class TemplateIntelligenceResponse(BaseModel):
    template_family: str
    style_preset: str
    cta_intent: str
    recommended_scene_count: int


# ---------------------------------------------------------------------------
# Combo recommender schemas
# ---------------------------------------------------------------------------


class ComboRecommendRequest(BaseModel):
    content_goal: str = Field(..., min_length=1)
    market_code: Optional[str] = None
    conversion_mode: Optional[str] = None
    candidate_avatars: list[dict[str, Any]] = Field(default_factory=list)


class ComboRecommendResponse(BaseModel):
    avatar_id: Optional[str] = None
    avatar_name: Optional[str] = None
    template_family: str
    cta_intent: str
    style_preset: str
    recommended_scene_count: int
    estimated_conversion_score: float
    rationale: str


# ---------------------------------------------------------------------------
# Analytics action schemas
# ---------------------------------------------------------------------------


class AnalyticsActionRequest(BaseModel):
    conversion_score: float = Field(..., ge=0.0, le=1.0)
    details: dict[str, Any] = Field(default_factory=dict)
    content_goal: Optional[str] = None
    market_code: Optional[str] = None
    current_template_family: Optional[str] = None


class AnalyticsActionItem(BaseModel):
    action: str
    reason: str
    suggestion: str
    priority: str


class AnalyticsActionResponse(BaseModel):
    suggestion_count: int
    actions: list[AnalyticsActionItem]


# ---------------------------------------------------------------------------
# Learning engine schemas
# ---------------------------------------------------------------------------


class RecordPerformanceRequest(BaseModel):
    video_id: str = Field(..., min_length=1)
    hook_pattern: str = Field(..., min_length=1)
    cta_pattern: str = Field(..., min_length=1)
    template_family: str = Field(..., min_length=1)
    conversion_score: float = Field(..., ge=0.0, le=1.0)
    view_count: int = 0
    click_through_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class FeedbackSummaryResponse(BaseModel):
    total_records: int
    top_hook_patterns: list[dict[str, Any]]
    top_cta_patterns: list[dict[str, Any]]
    top_template_families: list[dict[str, Any]]
    avg_conversion_score: float
