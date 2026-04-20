from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LookbookRequest(BaseModel):
    collection_name: str | None = None
    products: list[dict[str, Any]] = Field(default_factory=list)
    market_code: str | None = None
    style_preset: str | None = None
    target_platform: str | None = None


class LookbookResponse(BaseModel):
    lookbook_id: str
    outfit_sequences: list[dict[str, Any]] = Field(default_factory=list)
    scene_pack: list[dict[str, Any]] = Field(default_factory=list)
    video_plan: dict[str, Any] = Field(default_factory=dict)
