"""avatar_acting — REST API for Avatar Acting Model.

Endpoints
---------
POST /api/v1/avatar/acting/build
    Build a full acting decision for a given avatar profile + story beat.
    Useful for debugging and offline scene planning.

GET /api/v1/avatar/acting/presets
    Return all archetype acting presets.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.schemas.avatar_acting import AvatarActingOutput, AvatarActingProfileSchema
from app.services.avatar.acting.avatar_acting_engine import ARCHETYPE_PRESETS, AvatarActingEngine

router = APIRouter(tags=["avatar-acting"])

_acting_engine = AvatarActingEngine()


class _BuildRequest:
    pass


from pydantic import BaseModel


class ActingBuildRequest(BaseModel):
    avatar_profile: dict[str, Any]
    beat: dict[str, Any]
    relationship_state: dict[str, Any] | None = None
    memory_traces: list[dict[str, Any]] | None = None


@router.post("/api/v1/avatar/acting/build")
def build_acting_decision(payload: ActingBuildRequest) -> dict[str, Any]:
    """Return a structured acting decision for the given beat and avatar profile."""
    result = _acting_engine.build(
        avatar_profile=payload.avatar_profile,
        beat=payload.beat,
        relationship_state=payload.relationship_state,
        memory_traces=payload.memory_traces,
    )
    return {"ok": True, "data": result}


@router.get("/api/v1/avatar/acting/presets")
def get_archetype_presets() -> dict[str, Any]:
    """Return all built-in archetype acting presets."""
    return {"ok": True, "data": ARCHETYPE_PRESETS}
