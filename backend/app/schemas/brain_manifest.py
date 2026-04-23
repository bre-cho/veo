"""brain_manifest — output/planning schemas produced by the Brain Layer."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WinnerDNASummary(BaseModel):
    pattern_id: str | None = None
    pattern_type: str | None = None
    hook_core: str | None = None
    title_pattern: str | None = None
    thumbnail_logic: str | None = None
    score: float | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ContinuityContext(BaseModel):
    series_id: str | None = None
    episode_index: int | None = None
    episode_role: str | None = None
    unresolved_loops: list[str] = Field(default_factory=list)
    resolved_loops: list[str] = Field(default_factory=list)
    callback_targets: list[str] = Field(default_factory=list)
    continuity_constraints: dict[str, Any] = Field(default_factory=dict)


class BrainPlan(BaseModel):
    selected_series_id: str | None = None
    selected_episode_index: int | None = None
    episode_role: str | None = None
    winner_pattern_refs: list[str] = Field(default_factory=list)
    open_loop_targets: list[str] = Field(default_factory=list)
    callback_targets: list[str] = Field(default_factory=list)
    scene_strategy: list[dict[str, Any]] = Field(default_factory=list)
    pacing_strategy: dict[str, Any] = Field(default_factory=dict)
    cta_strategy: dict[str, Any] = Field(default_factory=dict)
    notes: dict[str, Any] = Field(default_factory=dict)


class BrainFeedbackPayload(BaseModel):
    project_id: str | None = None
    render_job_id: str | None = None
    publish_job_id: str | None = None
    platform: str | None = None
    status: str | None = None
    final_video_url: str | None = None
    title: str | None = None
    description: str | None = None
    thumbnail_url: str | None = None
    # Brain-aware render feedback fields (top-level for easy API use)
    series_id: str | None = None
    episode_index: int | None = None
    continuity_context: dict[str, Any] = Field(default_factory=dict)
    brain_plan: dict[str, Any] = Field(default_factory=dict)
    winner_dna_summary: dict[str, Any] = Field(default_factory=dict)
    market_code: str | None = None
    content_goal: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


# Aliases for backward-compat with older callers
BrainPreviewPayload = BrainFeedbackPayload
BrainRenderFeedback = BrainFeedbackPayload
BrainPublishFeedback = BrainFeedbackPayload
