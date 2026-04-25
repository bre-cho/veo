"""next_level_script_output — Output contract for the NextLevelScriptEngine."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VoiceActingMeta(BaseModel):
    """Full TTS/voice acting instruction set for a single segment."""

    tone: str = "documentary, calm"
    speed: str = "normal"
    pause: str = "normal"
    stress_words: List[str] = Field(default_factory=list)


class NextLevelScriptSegment(BaseModel):
    """Single narration segment in a multi-scene script."""

    id: int
    scene_id: str
    purpose: str = Field(
        ...,
        description=(
            "hook | escalation | reveal | twist | cliffhanger | callback | setup | context"
        ),
    )
    text: str
    subtext: str = ""
    intent: str = "hint"
    emotion: str = "tension"
    duration_sec: int = 8
    voice: VoiceActingMeta = Field(default_factory=VoiceActingMeta)


class ScriptScorecard(BaseModel):
    """5-axis quality scorecard."""

    hook_strength: int = 0
    tension_density: int = 0
    retention_power: int = 0
    binge_potential: int = 0
    overall: int = 0


class NextLevelScriptOutput(BaseModel):
    """Full output from ``NextLevelScriptEngine.generate()``."""

    project_id: str
    episode_id: str

    title: str
    selected_variant: str
    hook_versions: List[str]
    full_script: str

    segments: List[NextLevelScriptSegment]
    pacing_map: List[Dict[str, Any]] = Field(default_factory=list)
    retention_hooks: List[str] = Field(default_factory=list)
    open_loop_map: List[Dict[str, Any]] = Field(default_factory=list)

    score: ScriptScorecard = Field(default_factory=ScriptScorecard)

    # Strategy metadata
    hook_strategy: Optional[str] = None
