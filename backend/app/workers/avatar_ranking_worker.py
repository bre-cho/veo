from __future__ import annotations

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.marketplace.avatar_ranking_service import AvatarRankingService

_ranking_service = AvatarRankingService()


@celery_app.task(name="autovis.update_avatar_ranking")
def update_avatar_ranking_task(avatar_id: str) -> dict:
    db = SessionLocal()
    try:
        result = _ranking_service.update_ranking(db, avatar_id)
        return {"ok": True, **result}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="autovis.update_all_avatar_rankings")
def update_all_avatar_rankings_task() -> dict:
    from app.models.autovis import AvatarDna

    db = SessionLocal()
    try:
        avatars = db.query(AvatarDna).filter(AvatarDna.is_published.is_(True)).all()
        updated = 0
        for avatar in avatars:
            _ranking_service.update_ranking(db, avatar.id)
            updated += 1
        return {"ok": True, "updated_count": updated}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        db.close()
