from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.avatar.avatar_identity_engine import AvatarIdentityEngine

router = APIRouter(tags=["avatar-debug"])
_engine = AvatarIdentityEngine()


class AvatarDebugRequest(BaseModel):
    market_code: str | None = None
    content_goal: str | None = None
    topic_class: str | None = None
    preferred_avatar_id: str | None = None


@router.post("/api/v1/avatar/select")
async def avatar_select_debug(payload: AvatarDebugRequest):
    result = _engine.select_avatar(
        market_code=payload.market_code,
        content_goal=payload.content_goal,
        topic_class=payload.topic_class,
        preferred_avatar_id=payload.preferred_avatar_id,
    )
    return {"ok": True, "data": result.model_dump(), "error": None}
