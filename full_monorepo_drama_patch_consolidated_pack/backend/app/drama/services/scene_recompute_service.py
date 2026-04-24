from __future__ import annotations

from typing import Any, Dict, Iterable, List
from uuid import UUID

from sqlalchemy.orm import Session

from app.drama.services.continuity_service import ContinuityService
from app.drama.services.state_query_service import StateQueryService


class SceneRecomputeService:
    """Rebuilds downstream scene continuity after mid-episode edits.

    Current version focuses on orchestration contract and leaves the heavy
    re-analysis work to the scene worker / compiler already defined in earlier phases.
    """

    def __init__(self, db: Session):
        self.db = db
        self.state_query_service = StateQueryService(db)
        self.continuity_service = ContinuityService(db)

    def recompute_episode_from_scene(
        self,
        episode_id: UUID,
        starting_scene_id: UUID,
        ordered_scene_ids: Iterable[UUID],
    ) -> Dict[str, Any]:
        scene_ids = list(ordered_scene_ids)
        drift_report: List[Dict[str, Any]] = []
        for previous_scene_id, current_scene_id in zip(scene_ids, scene_ids[1:]):
            previous_state = self.state_query_service.get_scene_state(previous_scene_id)
            current_state = self.state_query_service.get_scene_state(current_scene_id)
            if previous_state is None or current_state is None:
                continue
            continuity = self.continuity_service.compare(previous_state=previous_state, current_state=current_state)
            if continuity.get("has_break"):
                drift_report.append(
                    {
                        "previous_scene_id": previous_scene_id,
                        "current_scene_id": current_scene_id,
                        "continuity": continuity,
                    }
                )
        return {
            "episode_id": episode_id,
            "starting_scene_id": starting_scene_id,
            "scene_count": len(scene_ids),
            "drift_count": len(drift_report),
            "drift_report": drift_report,
        }
