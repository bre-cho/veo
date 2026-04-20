from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.scoring import CandidateScore


class LookbookRequest(BaseModel):
    collection_name: str | None = None
    products: list[dict[str, Any]] = Field(default_factory=list)
    market_code: str | None = None
    style_preset: str | None = None
    target_platform: str | None = None


class LookbookResponse(BaseModel):
    run_id: str | None = None
    lookbook_id: str
    outfit_sequences: list[dict[str, Any]] = Field(default_factory=list)
    scene_pack: list[dict[str, Any]] = Field(default_factory=list)
    video_plan: dict[str, Any] = Field(default_factory=dict)
    candidates: list[CandidateScore] = Field(default_factory=list)
    winner_candidate_id: str | None = None
