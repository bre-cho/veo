"""next_level_script_request — Input contract for the NextLevelScriptEngine.

Extends the single-scene ``ScriptRequest`` to support multi-scene episodes.
Key differences:
- ``scene_contexts``: list of scene dicts (one per scene in the episode)
- ``open_loops`` / ``unresolved_conflicts``: list of dicts (not plain strings)
- ``target_duration_min``: target episode duration in minutes
- ``variants``: number of hook candidates to generate for A/B selection
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NextLevelScriptRequest(BaseModel):
    """Full input contract for ``NextLevelScriptEngine.generate()``."""

    project_id: str
    episode_id: str

    drama_state: Dict[str, Any] = Field(
        ...,
        description=(
            "Drama state dict.  Must contain at least ``tension_score`` (0–100). "
            "Other keys: outcome_type, dominant_character_id, etc."
        ),
    )
    relationship_snapshot: Dict[str, Any] = Field(default_factory=dict)
    subtext_map: List[Dict[str, Any]] = Field(default_factory=list)
    power_shift: Dict[str, Any] = Field(default_factory=dict)
    memory_traces: List[Dict[str, Any]] = Field(default_factory=list)
    arc_progress: Dict[str, Any] = Field(default_factory=dict)

    # Multi-scene: ordered list of scene context dicts
    scene_contexts: List[Dict[str, Any]] = Field(
        ...,
        description=(
            "Ordered list of scene contexts for this episode. "
            "Each dict may include scene_id, hidden_intent, hidden_conflict, etc."
        ),
    )

    # Binge-chain memory: open loops from previous episodes
    open_loops: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list,
        description=(
            "Open loops from previous scenes/episodes.  "
            "Each dict may contain ``callback_line`` and ``loop_id``."
        ),
    )
    unresolved_conflicts: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list,
        description="Unresolved conflicts carried over from prior episodes.",
    )

    target_duration_min: int = Field(
        default=15,
        ge=1,
        description="Target total episode duration in minutes.",
    )
    variants: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of hook variants to generate for A/B selection.",
    )
