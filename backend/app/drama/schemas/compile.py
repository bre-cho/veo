from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

from pydantic import BaseModel, Field


class CompileEpisodeRequest(BaseModel):
    project_id: UUID
    episode_id: UUID
    force_recompute: bool = False


class CompileProjectRequest(BaseModel):
    project_id: UUID
    force_recompute: bool = False


class CompileEpisodeResponse(BaseModel):
    project_id: UUID
    episode_id: UUID
    scene_count: int
    compiled_scenes: List[Dict[str, Any]] = Field(default_factory=list)
    continuity_warnings: List[Dict[str, Any]] = Field(default_factory=list)


class CompileProjectResponse(BaseModel):
    project_id: UUID
    episode_count: int
    scene_count: int
    compiled_scenes: List[Dict[str, Any]] = Field(default_factory=list)
    continuity_warnings: List[Dict[str, Any]] = Field(default_factory=list)
