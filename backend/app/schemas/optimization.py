from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.scoring import CandidateScore


class OptimizationInput(BaseModel):
    project_id: str | None = None
    render_job_id: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    preview_payload: dict[str, Any] | None = None
    market_code: str | None = None
    content_goal: str | None = None
    conversion_mode: str | None = None


class OptimizationSuggestion(BaseModel):
    type: str
    priority: str
    message: str
    target_scene_index: int | None = None
    replacement_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OptimizationResponse(BaseModel):
    run_id: str | None = None
    rewrite_suggestions: list[OptimizationSuggestion] = Field(default_factory=list)
    new_hook_variant: str | None = None
    new_cta_variant: str | None = None
    scene_priority_changes: list[dict[str, Any]] = Field(default_factory=list)
    score_delta_estimate: float | None = None
    candidates: list[CandidateScore] = Field(default_factory=list)
    winner_candidate_id: str | None = None
    winner_rationale: str | None = None
