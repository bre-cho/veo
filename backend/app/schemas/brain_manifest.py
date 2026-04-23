"""brain_manifest — output/planning schemas produced by the Brain Layer."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ContinuityContext(BaseModel):
    series_id: str | None = None
    episode_index: int | None = None
    unresolved_loops: list[str] = Field(default_factory=list)
    resolved_loops: list[str] = Field(default_factory=list)
    callback_targets: list[str] = Field(default_factory=list)
    continuity_constraints: dict[str, Any] = Field(default_factory=dict)


class WinnerDNASummary(BaseModel):
    top_pattern_id: str | None = None
    hook_pattern: str | None = None
    title_pattern: str | None = None
    pacing_pattern: str | None = None
    cta_pattern: str | None = None
    scene_sequence_pattern: str | None = None
    confidence: float = 0.0
    extra: dict[str, Any] = Field(default_factory=dict)


class BrainPlan(BaseModel):
    selected_series_id: str | None = None
    selected_episode_index: int | None = None
    episode_role: str | None = None  # opener / escalation / reveal / bridge / payoff
    winner_pattern_refs: list[str] = Field(default_factory=list)
    open_loop_targets: list[str] = Field(default_factory=list)
    callback_targets: list[str] = Field(default_factory=list)
    scene_strategy: list[dict[str, Any]] = Field(default_factory=list)
    pacing_strategy: dict[str, Any] = Field(default_factory=dict)
    cta_strategy: dict[str, Any] = Field(default_factory=dict)
    extra: dict[str, Any] = Field(default_factory=dict)


class BrainPreviewPayload(BaseModel):
    """Extended preview payload carrying all Brain Layer decisions."""
    brain_plan: BrainPlan | None = None
    continuity_context: ContinuityContext | None = None
    winner_dna_summary: WinnerDNASummary | None = None
    memory_refs: dict[str, Any] = Field(default_factory=dict)


class BrainRenderFeedback(BaseModel):
    project_id: str | None = None
    render_job_id: str | None = None
    final_video_url: str | None = None
    scene_statuses: list[dict[str, Any]] = Field(default_factory=list)
    continuity_context: dict[str, Any] = Field(default_factory=dict)
    brain_plan: dict[str, Any] = Field(default_factory=dict)
    winner_dna_summary: dict[str, Any] = Field(default_factory=dict)


class BrainPublishFeedback(BaseModel):
    project_id: str | None = None
    publish_job_id: str | None = None
    platform: str | None = None
    title: str | None = None
    description: str | None = None
    thumbnail_url: str | None = None
    signal_metrics: dict[str, Any] = Field(default_factory=dict)
