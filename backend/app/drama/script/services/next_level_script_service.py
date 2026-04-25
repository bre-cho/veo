"""next_level_script_service — service wrapper for NextLevelScriptEngine."""
from __future__ import annotations

from app.drama.script.engines.script_engine import NextLevelScriptEngine
from app.drama.script.schemas.next_level_script_request import NextLevelScriptRequest
from app.drama.script.schemas.next_level_script_output import NextLevelScriptOutput

_engine = NextLevelScriptEngine()


def generate_next_level_script(request: NextLevelScriptRequest) -> NextLevelScriptOutput:
    """Generate a cinematic multi-scene script from a ``NextLevelScriptRequest``.

    This is the primary entry point used by the API route and any downstream
    orchestration layer that needs full episode script generation.
    """
    return _engine.generate(request)
