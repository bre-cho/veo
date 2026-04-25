"""script_output — Output contract for the Script Generation Engine."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VoiceDirective(BaseModel):
    """TTS/voice acting instructions for a segment."""

    pause: str = "normal"      # "none" | "short" | "normal" | "long"
    speed: str = "normal"      # "slow" | "normal" | "fast"
    tone: str = "neutral"      # "neutral" | "low" | "whisper" | "intense"


class ScriptSegment(BaseModel):
    """Single narration segment in the output script."""

    id: int
    purpose: str = Field(
        ...,
        description="hook | escalation | reveal | twist | cliffhanger | callback | setup | context",
    )
    text: str
    subtext: Optional[str] = None
    emotion: Optional[str] = None
    intent: Optional[str] = None      # dominate | destabilize | mislead | hint
    duration_sec: float = 4.0
    voice: VoiceDirective = Field(default_factory=VoiceDirective)


class ScriptOutput(BaseModel):
    """Full script output from ``ScriptEngine.generate()``."""

    project_id: str
    scene_id: str

    title: str
    hook: str
    segments: List[ScriptSegment]
    full_script: str

    pacing_map: List[Dict[str, Any]] = Field(default_factory=list)
    retention_hooks: List[str] = Field(default_factory=list)
    retention_score: int = 0

    voice_style: str = "neutral documentary"

    # Strategy metadata (for logging / feedback)
    hook_strategy: Optional[str] = None
