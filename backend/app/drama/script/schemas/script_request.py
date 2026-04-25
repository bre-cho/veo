"""script_request — Input contract for the Script Generation Engine.

The engine receives structured drama state from the Brain Layer and produces a
deterministic voiceover script.  It does NOT call an LLM directly.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DramaStateInput(BaseModel):
    """Subset of drama state needed by the script engine."""

    tension_score: float = Field(
        ..., ge=0.0, le=100.0, description="0–100 tension score from TensionEngine."
    )
    dominant_character_id: Optional[str] = None
    threatened_character_id: Optional[str] = None
    outcome_type: Optional[str] = Field(
        None,
        description="e.g. 'betrayal', 'revelation', 'confrontation', 'reconciliation'",
    )
    turning_point: Optional[str] = None


class SceneContextInput(BaseModel):
    """Scene-level context that anchors the narrative."""

    scene_goal: Optional[str] = None
    visible_conflict: Optional[str] = None
    hidden_conflict: Optional[str] = None
    participants: List[str] = Field(default_factory=list)


class SubtextItem(BaseModel):
    """Single subtext entry from the SubtextEngine."""

    character_id: Optional[str] = None
    hidden_intent: Optional[str] = None
    surface_text: Optional[str] = None
    emotional_charge: Optional[float] = None


class MemoryTrace(BaseModel):
    """A narrative wound or memory that may surface in the script."""

    character_id: Optional[str] = None
    memory_type: Optional[str] = None
    summary: Optional[str] = None
    intensity: Optional[float] = None


class ScriptRequest(BaseModel):
    """Full input contract for ``ScriptEngine.generate()``."""

    project_id: str
    scene_id: str
    episode_id: Optional[str] = None

    drama_state: DramaStateInput
    relationship_snapshot: Dict[str, Any] = Field(default_factory=dict)
    subtext_map: List[SubtextItem] = Field(default_factory=list)
    power_shift: Dict[str, Any] = Field(default_factory=dict)
    memory_traces: List[MemoryTrace] = Field(default_factory=list)
    arc_progress: Dict[str, Any] = Field(default_factory=dict)

    scene_context: SceneContextInput = Field(default_factory=SceneContextInput)

    # Binge-chain memory: open loops from previous scenes
    previous_scene_summary: Optional[str] = None
    open_loops: List[str] = Field(default_factory=list)
    unresolved_conflicts: List[str] = Field(default_factory=list)
