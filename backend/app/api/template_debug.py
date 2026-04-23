"""template_debug — lightweight endpoint for verifying template selection logic.

Useful during development / QA to confirm that TemplateSelector returns the
expected template for a given topic/context without going through the full
Brain Layer pipeline.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.template.template_selector import TemplateSelector

router = APIRouter(tags=["template-debug"])
_selector = TemplateSelector()


class TemplateDebugRequest(BaseModel):
    topic: str | None = None
    script_text: str | None = None
    market_code: str | None = None
    content_goal: str | None = None
    episode_role: str | None = "continuation"


@router.post("/api/v1/template/select")
async def template_select_debug(payload: TemplateDebugRequest):
    result = _selector.select(
        request=payload.model_dump(),
        memory_bundle={},
        continuity={"episode_role": payload.episode_role},
    )
    return {"ok": True, "data": result.model_dump(), "error": None}
