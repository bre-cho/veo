from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PatternMemoryIn(BaseModel):
    pattern_type: str
    market_code: str | None = None
    content_goal: str | None = None
    source_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    score: float | None = None


class PatternMemoryOut(BaseModel):
    pattern_id: str
    pattern_type: str
    market_code: str | None = None
    content_goal: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    score: float | None = None
    created_at: str
