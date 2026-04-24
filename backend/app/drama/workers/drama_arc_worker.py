from __future__ import annotations

from celery import shared_task
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.drama.services.arc_service import ArcService


@shared_task(name="app.drama.workers.recompute_arcs")
def recompute_arcs(project_id: str, episode_id: str | None = None) -> dict:
    db: Session = SessionLocal()
    try:
        service = ArcService(db)
        if episode_id:
            updated = service.recompute_for_episode(project_id=project_id, episode_id=episode_id)
        else:
            updated = service.recompute_for_project(project_id=project_id)
        db.commit()
        return {"ok": True, "project_id": project_id, "episode_id": episode_id, "updated": updated}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
