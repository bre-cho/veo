"""drama_script API — Script Generation Engine endpoint.

POST /api/v1/drama/script/generate
"""
from __future__ import annotations

from fastapi import APIRouter

from app.drama.script.schemas.script_request import ScriptRequest
from app.drama.script.schemas.script_output import ScriptOutput
from app.drama.script.services.script_service import generate_script

router = APIRouter(tags=["drama-script"])


@router.post(
    "/api/v1/drama/script/generate",
    response_model=ScriptOutput,
    summary="Generate a voiceover script from drama state",
)
def generate_script_endpoint(payload: ScriptRequest) -> ScriptOutput:
    """Generate a deterministic voiceover script from structured drama state.

    The engine uses Brain Layer outputs (drama_state, subtext_map,
    memory_traces, etc.) to build a retention-optimised voiceover script
    without calling an LLM directly.
    """
    return generate_script(payload)
