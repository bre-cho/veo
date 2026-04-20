from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CandidateScore(BaseModel):
    candidate_id: str
    score_total: float
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    winner_flag: bool = False
    rationale: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
