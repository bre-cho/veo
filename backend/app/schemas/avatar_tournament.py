"""avatar_tournament — request/response schemas for the avatar tournament engine."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class AvatarCandidateScore(BaseModel):
    """Scored and ranked candidate avatar within a tournament run."""

    avatar_id: str
    template_id: str | None = None
    predicted_score: float = 0.0
    predicted_ctr: float | None = None
    predicted_retention: float | None = None
    predicted_conversion: float | None = None
    continuity_score: float | None = None
    brand_fit_score: float | None = None
    pair_fit_score: float | None = None
    governance_penalty: float = 0.0
    final_rank_score: float = 0.0


class AvatarTournamentRequest(BaseModel):
    """Input to run an avatar selection tournament."""

    workspace_id: str
    project_id: str | None = None
    topic_signature: str | None = None
    template_family: str | None = None
    platform: str | None = None
    candidate_avatar_ids: list[str] = Field(default_factory=list)
    exploration_ratio: float = Field(default=0.15, ge=0.0, le=1.0)
    force_avatar_ids: list[str] = Field(default_factory=list)
    # Optional context passed through from Brain Layer
    market_code: str | None = None
    content_goal: str | None = None
    topic_class: str | None = None
    preferred_avatar_id: str | None = None


class AvatarTournamentResult(BaseModel):
    """Output of a completed avatar selection tournament."""

    tournament_run_id: str
    selected_avatar_id: str
    ranked_candidates: list[AvatarCandidateScore]
    selection_mode: str  # exploit|explore|forced_test
    explanation: dict[str, Any] = Field(default_factory=dict)
