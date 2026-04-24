from __future__ import annotations

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.drama.models.scene_drama_state import DramaSceneState
from app.drama.services.continuity_service import ContinuityService


@shared_task(name="app.drama.workers.rebuild_continuity")
def rebuild_continuity(project_id: str, episode_id: str | None = None) -> dict:
    """Recompute continuity drift across stored scene states.

    Intended use cases:
    - scene edit in the middle of an episode
    - arc repair pass after manual overrides
    - nightly quality sweep
    """
    db: Session = SessionLocal()
    try:
        continuity_service = ContinuityService()
        stmt = select(DramaSceneState).where(DramaSceneState.project_id == project_id)
        if episode_id:
            stmt = stmt.where(DramaSceneState.episode_id == episode_id)
        stmt = stmt.order_by(DramaSceneState.created_at.asc())
        scene_states = db.execute(stmt).scalars().all()

        previous = None
        reports: list[dict] = []
        for current in scene_states:
            analysis = current.analysis_payload or {}
            if previous is None:
                current.continuity_payload = {"ok": True, "reason": "first_scene"}
            else:
                report = continuity_service.check_continuity(previous.analysis_payload or {}, analysis)
                current.continuity_payload = report
                reports.append({"scene_id": str(current.scene_id), **report})
            db.add(current)
            previous = current

        db.commit()
        return {"ok": True, "project_id": project_id, "episode_id": episode_id, "reports": reports}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
