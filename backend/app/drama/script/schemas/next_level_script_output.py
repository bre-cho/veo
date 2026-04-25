from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ScriptSegment(BaseModel):
    scene_id: str
    text: str
    purpose: Optional[str] = None
    duration_sec: int = 6
    subtext: Optional[str] = None
    intent: Optional[str] = None
    emotion: Optional[str] = None
    voice: Optional[Dict[str, Any]] = None


class NextLevelScriptOutput(BaseModel):
    full_script: str
    segments: List[Dict[str, Any]] = []
    render_scenes: Optional[List[Dict[str, Any]]] = None
