from __future__ import annotations

from typing import Any, Dict, List, Literal

try:
    from pydantic import BaseModel

    RebuildStrategyType = Literal[
        "changed_only",
        "dependency_set",
        "affected_range",
        "full_rebuild",
    ]

    class RebuildStrategyEstimate(BaseModel):
        strategy: RebuildStrategyType
        scene_ids: List[str]
        estimated_cost: float
        estimated_time_sec: float
        safe: bool
        reason: str
        details: Dict[str, Any] = {}

except ImportError:  # pragma: no cover
    pass
