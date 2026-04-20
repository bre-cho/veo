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

    For each avatar the scheduler:
    1. Checks the render repository for recently completed render outputs.
    2. Uses ``MediaEmbeddingExtractor`` to sample ``_TOP_N_FRAMES`` distinct
       frame embeddings from each render URL.
    3. Passes those embeddings to ``CanonicalReferenceRefresher`` which selects
       the highest-quality frame and upserts it as the new canonical reference.

    When no completed renders exist for an avatar (e.g. new avatar with no
    renders yet), the existing canonical frame is left unchanged.  Unlike the
    previous implementation, the scheduler never writes synthetic duplicates of
    the same embedding.
    """
    from app.services.avatar.avatar_identity_service import CanonicalReferenceRefresher
    from app.services.avatar.media_embedding_extractor import MediaEmbeddingExtractor

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
    skipped = 0
    try:
        from app.models.autovis import AvatarVisualDna
        avatar_ids = list({row.avatar_id for row in db.query(AvatarVisualDna).all()})
        refresher = CanonicalReferenceRefresher()
        extractor = MediaEmbeddingExtractor()

        for avatar_id in avatar_ids:
            try:
                render_frames = _collect_render_frames(db, avatar_id, extractor)
                if not render_frames:
                    # No completed renders available — skip this avatar
                    skipped += 1
                    logger.debug(
                        "canonical_reference_scheduler: no render frames for avatar=%s, skipping",
                        avatar_id,
                    )
                    continue
                refresher.refresh_after_success(db, avatar_id, render_frames)
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

    logger.info(
        "canonical_reference_scheduler: refreshed=%d skipped=%d",
        refreshed,
        skipped,
    )
    return {"avatars_refreshed": refreshed, "avatars_skipped": skipped}


def _collect_render_frames(
    db: Any,
    avatar_id: str,
    extractor: "MediaEmbeddingExtractor",
) -> list[list[float]]:
    """Return up to ``_TOP_N_FRAMES`` per-frame embeddings from real render outputs.

    Queries the render repository for recently completed renders associated
    with this avatar, samples one frame per render from its output URL, and
    returns the collected embeddings.  Returns an empty list when no completed
    renders are available.
    """
    render_urls: list[str] = _find_recent_render_urls(db, avatar_id)
    if not render_urls:
        return []

    frames: list[list[float]] = []
    for url in render_urls[:_TOP_N_FRAMES]:
        try:
            # Sample a single representative embedding per render output
            emb = extractor.extract(url, n_frames=1)
            frames.append(emb)
        except Exception as exc:
            logger.debug(
                "canonical_reference_scheduler: extraction failed url=%s avatar=%s: %s",
                url, avatar_id, exc,
            )
    return frames


def _find_recent_render_urls(db: Any, avatar_id: str) -> list[str]:
    """Return output URLs of recently completed renders for an avatar.

    Looks up ``RenderJob`` rows (or equivalent model) where the render is
    completed and the payload references the given ``avatar_id``.  Falls back
    gracefully when the render model is unavailable.
    """
    try:
        from app.models.render_job import RenderJob  # type: ignore[import]
        from datetime import datetime, timedelta, timezone

        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
        rows = (
            db.query(RenderJob)
            .filter(
                RenderJob.status == "completed",
                RenderJob.updated_at >= cutoff,
            )
            .order_by(RenderJob.updated_at.desc())
            .limit(_TOP_N_FRAMES * 3)  # fetch extra; filter by avatar_id below
            .all()
        )
        urls: list[str] = []
        for row in rows:
            payload: dict = row.payload or {}
            if str(payload.get("avatar_id", "")) == avatar_id:
                output_url = str(payload.get("output_url") or payload.get("render_url") or "").strip()
                if output_url:
                    urls.append(output_url)
            if len(urls) >= _TOP_N_FRAMES:
                break
        return urls
    except Exception:
        return []


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
