from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from app.render.assembly.schemas.assembly_request import AssemblyRequest
from app.render.assembly.services.assembly_service import AssemblyService

router = APIRouter(prefix="/api/v1/render/assembly", tags=["render-assembly"])

service = AssemblyService()


@router.post("/execute")
def execute_assembly(payload: AssemblyRequest) -> Dict[str, Any]:
    """Execute the FFmpeg final assembly pass for a compiled episode.

    Reads the ``assembly_plan`` (produced by the Scene Timeline Compiler),
    resolves all scene video/audio assets, writes karaoke subtitles, and
    runs FFmpeg to produce the final MP4.
    """
    return service.assemble(payload)
