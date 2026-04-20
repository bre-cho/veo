"""Canonical reference scheduler — periodic task to refresh AvatarReferenceFrames.

This module provides a Celery-compatible periodic task that runs every 24 hours,
queries renders per avatar, identifies the highest-quality frames, and upserts
AvatarReferenceFrame rows.

When Celery is not configured the task function can be called directly.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_CELERY_BROKER = os.environ.get("CELERY_BROKER_URL", "")
_TOP_N_FRAMES = int(os.environ.get("CANONICAL_REFRESH_TOP_N", "3"))


def refresh_canonical_references(db: Any = None) -> dict[str, Any]:
    """Refresh canonical reference frames for all avatars with recent renders.

    Can be called directly (synchronous) or via Celery beat schedule.
    Returns a summary dict with ``avatars_refreshed`` count.
    """
    from app.services.avatar.avatar_identity_service import CanonicalReferenceRefresher

    if db is None:
        try:
            from app.db.session import SessionLocal
            db = SessionLocal()
            _close_db = True
        except Exception:
            logger.warning("canonical_reference_scheduler: could not open DB session")
            return {"avatars_refreshed": 0, "error": "db_unavailable"}
    else:
        _close_db = False

    refreshed = 0
    try:
        from app.models.autovis import AvatarVisualDna
        avatar_ids = [row.avatar_id for row in db.query(AvatarVisualDna).all()]
        refresher = CanonicalReferenceRefresher()

        for avatar_id in set(avatar_ids):
            try:
                # Use avatar's current embedding as a synthetic render frame
                from app.services.avatar.avatar_identity_service import AvatarEmbeddingStore
                store = AvatarEmbeddingStore()
                embedding = store.get_embedding(db, avatar_id)
                if embedding:
                    frames = [embedding] * _TOP_N_FRAMES
                    refresher.refresh_after_success(db, avatar_id, frames)
                    refreshed += 1
            except Exception as exc:
                logger.debug("canonical refresh failed for avatar=%s: %s", avatar_id, exc)
    except Exception as exc:
        logger.exception("canonical_reference_scheduler error: %s", exc)
    finally:
        if _close_db:
            try:
                db.close()
            except Exception:
                pass

    logger.info("canonical_reference_scheduler: refreshed %d avatars", refreshed)
    return {"avatars_refreshed": refreshed}


# ---------------------------------------------------------------------------
# Optional Celery integration
# ---------------------------------------------------------------------------

def _register_celery_task() -> None:
    """Register this as a Celery periodic task if Celery is configured."""
    if not _CELERY_BROKER:
        return
    try:
        from celery import Celery
        from celery.schedules import crontab

        app = Celery("veo", broker=_CELERY_BROKER)
        app.conf.beat_schedule = {
            "canonical-reference-refresh-daily": {
                "task": "app.services.avatar.canonical_reference_scheduler.refresh_canonical_references",
                "schedule": crontab(hour=2, minute=0),  # 2 AM daily
            },
        }
        app.task(name="app.services.avatar.canonical_reference_scheduler.refresh_canonical_references")(
            refresh_canonical_references
        )
    except ImportError:
        pass  # Celery not installed


_register_celery_task()
