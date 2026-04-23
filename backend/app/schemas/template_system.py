"""template_system — schema definitions for the Template Selection System."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TemplatePromptBias(BaseModel):
    tone: str | None = None
    contrast: str | None = None
    emotion: str | None = None
    visual_density: str | None = None


class TemplateBestFor(BaseModel):
    content_goal: list[str] = Field(default_factory=list)
    market_code: list[str] = Field(default_factory=list)
    topic_classes: list[str] = Field(default_factory=list)


class TemplateDefinition(BaseModel):
    template_id: str
    template_family: str
    narrative_mode: str
    hook_strategy: str
    scene_sequence: list[str] = Field(default_factory=list)
    pacing_profile: dict[str, float] = Field(default_factory=dict)
    shot_profile: dict[str, str] = Field(default_factory=dict)
    prompt_bias: TemplatePromptBias = Field(default_factory=TemplatePromptBias)
    cta_style: str | None = None
    best_for: TemplateBestFor = Field(default_factory=TemplateBestFor)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TemplateSelectionResult(BaseModel):
    template_id: str
    template_family: str
    score: float
    reasons: list[str] = Field(default_factory=list)
    template_payload: dict[str, Any] = Field(default_factory=dict)


class TemplateVariantResult(BaseModel):
    template_id: str
    variant_id: str
    score: float
    payload: dict[str, Any] = Field(default_factory=dict)
