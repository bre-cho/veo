from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from app.drama.timeline.schemas.timeline_request import TimelineRequest
from app.drama.timeline.services.timeline_service import TimelineService

router = APIRouter(prefix="/api/v1/drama/timeline", tags=["drama-timeline"])

service = TimelineService()


@router.post("/compile")
def compile_timeline(payload: TimelineRequest) -> Dict[str, Any]:
    """Compile render scenes into a full scene timeline with timing data."""
    return service.compile(payload)
