"""drama_script API — Script Generation Engine endpoints.

POST /api/v1/drama/script/generate            — single-scene
POST /api/v1/drama/script/next-level-generate — multi-scene (episode-level)
"""
from __future__ import annotations

from fastapi import APIRouter

from app.drama.script.schemas.script_request import ScriptRequest
from app.drama.script.schemas.script_output import ScriptOutput
from app.drama.script.schemas.next_level_script_request import NextLevelScriptRequest
from app.drama.script.schemas.next_level_script_output import NextLevelScriptOutput
from app.drama.script.services.script_service import generate_script
from app.drama.script.services.next_level_script_service import generate_next_level_script

router = APIRouter(tags=["drama-script"])


@router.post(
    "/api/v1/drama/script/generate",
    response_model=ScriptOutput,
    summary="Generate a voiceover script from drama state (single scene)",
)
def generate_script_endpoint(payload: ScriptRequest) -> ScriptOutput:
    """Generate a deterministic voiceover script from structured drama state.

    The engine uses Brain Layer outputs (drama_state, subtext_map,
    memory_traces, etc.) to build a retention-optimised voiceover script
    without calling an LLM directly.
    """
    return generate_script(payload)


@router.post(
    "/api/v1/drama/script/next-level-generate",
    response_model=NextLevelScriptOutput,
    summary="Generate a cinematic multi-scene script (episode-level)",
)
def generate_next_level_script_endpoint(
    payload: NextLevelScriptRequest,
) -> NextLevelScriptOutput:
    """Generate a full episode script using the Cinematic Script Intelligence Engine.

    Upgrades over the single-scene endpoint:
    - Multi-scene sequence planning
    - A/B hook variant generation with best-hook selection
    - Per-scene intent classification
    - Binge-chain callback injection from previous episodes
    - Full voice-acting directives per segment
    - 5-axis script quality scorecard
    """
    return generate_next_level_script(payload)
