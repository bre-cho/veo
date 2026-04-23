"""template_evolution — schemas for template evolution candidates and batches."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TemplateEvolutionCandidate(BaseModel):
    candidate_id: str
    template_id: str
    template_family: str
    origin_type: str  # mutation | crossover | distillation
    parent_template_ids: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    evolution_notes: dict[str, Any] = Field(default_factory=dict)
    status: str = "candidate"  # candidate | testing | promoted | rejected


class TemplateEvolutionBatch(BaseModel):
    batch_id: str
    source_template_ids: list[str] = Field(default_factory=list)
    candidates: list[TemplateEvolutionCandidate] = Field(default_factory=list)
