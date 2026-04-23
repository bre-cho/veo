from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AutopilotBrainCompileRequest(BaseModel):
    topic: str | None = Field(default=None)
    script_text: str | None = Field(default=None)
    audience: str | None = None
    platform: str = Field(default="youtube")
    market_code: str | None = None
    niche: str | None = None
    channel_name: str | None = None
    store_if_winner: bool = False


class BrainScorecard(BaseModel):
    attention: int
    retention: int
    trust: int
    conversion: int
    scaling: int
    total: int
    classification: str
    decision: Literal["BLOCK", "TEST", "WINNER", "SCALE", "DOMINATION"]


class BrainMemoryMatch(BaseModel):
    source_id: str | None = None
    score: float
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)


class BrainSeriesEpisode(BaseModel):
    episode_index: int
    working_title: str
    purpose: str
    unresolved_loop: str


class SEOBridge(BaseModel):
    title: str
    thumbnail_brief: str
    description: str
    pinned_comment: str
    video_hashtags: list[str] = Field(default_factory=list)
    channel_hashtags: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class AutopilotBrainCompileResponse(BaseModel):
    command_path: str
    scorecard: BrainScorecard
    memory_matches: list[BrainMemoryMatch] = Field(default_factory=list)
    series_map: list[BrainSeriesEpisode] = Field(default_factory=list)
    seo_bridge: SEOBridge
    runtime_memory_payload: dict[str, Any] = Field(default_factory=dict)
