"""script_service — thin service wrapper around ScriptEngine.

Provides a stable public interface for the API layer so the engine
implementation can evolve independently.
"""
from __future__ import annotations

from app.drama.script.engines.script_engine import ScriptEngine
from app.drama.script.schemas.script_request import ScriptRequest
from app.drama.script.schemas.script_output import ScriptOutput

_engine = ScriptEngine()


def generate_script(request: ScriptRequest) -> ScriptOutput:
    """Generate a voiceover script from structured drama state.

    This is the primary entry point used by the API route and any downstream
    orchestration layer that has received a validated ``ScriptRequest``.
    """
    return _engine.generate(request)
