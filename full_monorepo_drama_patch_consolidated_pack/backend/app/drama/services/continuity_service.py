from __future__ import annotations

from typing import Any, Dict, Optional

from app.drama.engines.continuity_engine import ContinuityEngine


class ContinuityService:
    """Thin orchestration layer for continuity checks.

    Replace in-memory lookup stubs with repository/database calls when integrating
    into the target monorepo.
    """

    def __init__(self) -> None:
        self.engine = ContinuityEngine()

    def inspect_scene_transition(
        self,
        scene_context: Dict[str, Any],
        current_analysis: Dict[str, Any],
        previous_scene_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        previous_scene_state = previous_scene_state or {}
        return self.engine.inspect_transition(
            previous_scene_state=previous_scene_state,
            current_scene_context=scene_context,
            current_analysis=current_analysis,
        )
