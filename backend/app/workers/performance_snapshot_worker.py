from __future__ import annotations

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.analytics.performance_snapshot_service import PerformanceSnapshotService

_snapshot_service = PerformanceSnapshotService()


@celery_app.task(name="autovis.capture_performance_snapshot")
def capture_performance_snapshot_task(avatar_id: str) -> dict:
    db = SessionLocal()
    try:
        result = _snapshot_service.capture(db, avatar_id)
        return {"ok": True, **result}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="autovis.capture_all_performance_snapshots")
def capture_all_performance_snapshots_task() -> dict:
    from app.models.autovis import AvatarDna

    db = SessionLocal()
    try:
        avatars = db.query(AvatarDna).filter(AvatarDna.is_published.is_(True)).all()
        captured = 0
        for avatar in avatars:
            _snapshot_service.capture(db, avatar.id)
            captured += 1
        return {"ok": True, "captured_count": captured}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        db.close()
