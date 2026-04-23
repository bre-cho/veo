from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class AvatarSelectionDebugView(BaseModel):
    avatar_id: UUID
    base_score: float = 0.0
    pair_bonus: float = 0.0
    continuity_bonus: float = 0.0
    exploration_bonus: float = 0.0
    governance_penalty: float = 0.0
    final_score: float = 0.0
    state: str = "candidate"
    explanation_lines: list[str] = Field(default_factory=list)
