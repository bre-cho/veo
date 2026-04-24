from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.drama.models.scene_drama_state import SceneDramaState
from app.drama.models.memory_trace import MemoryTrace
from app.drama.models.arc_progress import ArcProgress


class StateQueryService:
    def __init__(self, db: Session):
        self.db = db

    def get_scene_state(self, scene_id: UUID) -> Optional[SceneDramaState]:
        return (
            self.db.query(SceneDramaState)
            .filter(SceneDramaState.scene_id == scene_id)
            .order_by(desc(SceneDramaState.created_at))
            .first()
        )

    def get_latest_episode_state(self, episode_id: UUID, project_id: Optional[UUID] = None) -> Optional[Dict[str, Any]]:
        query = self.db.query(SceneDramaState).filter(SceneDramaState.episode_id == episode_id)
        if project_id is not None:
            query = query.filter(SceneDramaState.project_id == project_id)
        latest = query.order_by(desc(SceneDramaState.created_at)).first()
        if latest is None:
            return None
        return {
            "episode_id": latest.episode_id,
            "project_id": latest.project_id,
            "latest_scene_id": latest.scene_id,
            "latest_created_at": latest.created_at,
            "latest_outcome_type": latest.outcome_type,
            "latest_scene_temperature": latest.scene_temperature,
        }

    def get_project_dashboard(self, project_id: UUID) -> Dict[str, Any]:
        scene_count = self.db.query(func.count(SceneDramaState.id)).filter(SceneDramaState.project_id == project_id).scalar() or 0
        memory_count = (
            self.db.query(func.count(MemoryTrace.id))
            .join(SceneDramaState, SceneDramaState.scene_id == MemoryTrace.source_scene_id, isouter=True)
            .filter(SceneDramaState.project_id == project_id)
            .scalar()
            or 0
        )
        arc_count = self.db.query(func.count(ArcProgress.id)).filter(ArcProgress.episode_id.isnot(None)).scalar() or 0
        hottest_scene = (
            self.db.query(SceneDramaState)
            .filter(SceneDramaState.project_id == project_id)
            .order_by(desc(SceneDramaState.scene_temperature), desc(SceneDramaState.created_at))
            .first()
        )
        return {
            "project_id": project_id,
            "scene_state_count": scene_count,
            "memory_trace_count": memory_count,
            "arc_progress_count": arc_count,
            "hottest_scene_id": getattr(hottest_scene, "scene_id", None),
            "hottest_scene_temperature": getattr(hottest_scene, "scene_temperature", None),
        }
