"""avatar_selection_debug — schema for explaining why an avatar was chosen."""
from __future__ import annotations

from pydantic import BaseModel, Field


class AvatarSelectionDebugView(BaseModel):
    """Human-readable breakdown of why an avatar scored the way it did."""

    avatar_id: str
    base_score: float = 0.0
    pair_bonus: float = 0.0
    continuity_bonus: float = 0.0
    governance_penalty: float = 0.0
    exploration_bonus: float = 0.0
    final_score: float = 0.0
    state: str = "candidate"
    explanation_lines: list[str] = Field(default_factory=list)
