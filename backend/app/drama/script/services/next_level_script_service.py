from __future__ import annotations

from typing import Any, Dict

from app.drama.script.engines.script_engine import NextLevelScriptEngine
from app.drama.render.adapters.script_to_render_adapter import ScriptToRenderAdapter


class NextLevelScriptService:
    """Orchestrates script generation and attaches render-ready scene payloads."""

    def __init__(self) -> None:
        self.engine = NextLevelScriptEngine()
        self.render_adapter = ScriptToRenderAdapter()

    def generate(self, payload: Any) -> Dict[str, Any]:
        script_output = self.engine.generate(payload)
        render_scenes = self.render_adapter.adapt(script_output)
        script_output["render_scenes"] = render_scenes
        return script_output
