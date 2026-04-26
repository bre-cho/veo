"""next_level_script_service — service wrapper for NextLevelScriptEngine."""
from __future__ import annotations

from typing import Any, Dict

from app.drama.script.engines.script_engine import NextLevelScriptEngine
from app.drama.script.schemas.next_level_script_request import NextLevelScriptRequest
from app.drama.script.schemas.next_level_script_output import NextLevelScriptOutput
from app.drama.render.adapters.script_to_render_adapter import ScriptToRenderAdapter


class NextLevelScriptService:
    """Orchestrates script generation and attaches render-ready scene payloads."""

    def __init__(self) -> None:
        self.engine = NextLevelScriptEngine()
        self.render_adapter = ScriptToRenderAdapter()

    def generate(self, payload: NextLevelScriptRequest) -> Dict[str, Any]:
        """Generate a cinematic multi-scene script and attach render-ready scenes."""
        script_output: NextLevelScriptOutput = self.engine.generate(payload)
        output_dict = script_output.model_dump()
        output_dict["render_scenes"] = self.render_adapter.adapt(output_dict)
        return output_dict


def generate_next_level_script(payload: NextLevelScriptRequest) -> NextLevelScriptOutput:
    """Compatibility wrapper used by API modules importing function-level service."""
    service = NextLevelScriptService()
    output = service.generate(payload)
    return NextLevelScriptOutput.model_validate(output)
