from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict

from app.drama.engines.arc_engine import ArcEngine

router = APIRouter(prefix="/api/v1/drama/arcs", tags=["drama-arcs"])
engine = ArcEngine()


class AdvanceArcRequest(BaseModel):
    character_arc_state: Dict[str, Any]
    scene_analysis: Dict[str, Any]


@router.post("/advance")
def advance_arc(request: AdvanceArcRequest) -> Dict[str, Any]:
    return engine.advance_arc(
        character_arc_state=request.character_arc_state,
        scene_analysis=request.scene_analysis,
    )
