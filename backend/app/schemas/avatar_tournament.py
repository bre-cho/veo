from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AvatarCandidateScore(BaseModel):
    avatar_id: UUID
    template_id: UUID | None = None
    predicted_score: float = 0.0
    predicted_ctr: float | None = None
    predicted_retention: float | None = None
    predicted_conversion: float | None = None
    continuity_score: float | None = None
    brand_fit_score: float | None = None
    pair_fit_score: float | None = None
    pair_confidence: float | None = None
    governance_penalty: float | None = None
    final_rank_score: float = 0.0


class AvatarTournamentRequest(BaseModel):
    workspace_id: UUID
    project_id: UUID | None = None
    topic_id: UUID | None = None
    topic_signature: str | None = None
    template_family: str | None = None
    platform: str | None = None
    candidate_avatar_ids: list[UUID] = Field(default_factory=list)
    exploration_ratio: float = 0.15
    force_avatar_ids: list[UUID] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AvatarTournamentResult(BaseModel):
    tournament_run_id: UUID
    selected_avatar_id: UUID | None
    ranked_candidates: list[AvatarCandidateScore]
    selection_mode: str
    explanation: dict[str, Any]
    created_at: datetime | None = None
