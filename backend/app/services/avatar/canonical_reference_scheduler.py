"""Canonical reference scheduler — periodic task to refresh AvatarReferenceFrames.

This module provides a Celery-compatible periodic task that runs every 24 hours,
queries renders per avatar, identifies the highest-quality frames, and upserts
AvatarReferenceFrame rows.

Phase 2.2 additions:
- ``staleness_policy``: only refresh when canonical frame > CANONICAL_MAX_AGE_DAYS old
  **and** at least 1 new render exists in the window.
- ``drift_triggered_refresh``: auto-refresh when verify_render_output() similarity
  drops below _TEMPORAL_CONTINUITY_THRESHOLD 3 consecutive times.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

_CELERY_BROKER = os.environ.get("CELERY_BROKER_URL", "")
_TOP_N_FRAMES = int(os.environ.get("CANONICAL_REFRESH_TOP_N", "3"))
_CANONICAL_MAX_AGE_DAYS = int(os.environ.get("CANONICAL_MAX_AGE_DAYS", "7"))
_DRIFT_FAIL_THRESHOLD = int(os.environ.get("CANONICAL_DRIFT_FAIL_THRESHOLD", "3"))

# In-memory tracker for consecutive failed verifications per avatar
_drift_fail_counts: dict[str, int] = {}


def record_verification_failure(avatar_id: str) -> int:
    """Record a verification failure for drift-triggered refresh.

    Returns the updated consecutive failure count for this avatar.
    Call this from verify_render_output() when similarity < threshold.
    """
    _drift_fail_counts[avatar_id] = _drift_fail_counts.get(avatar_id, 0) + 1
    return _drift_fail_counts[avatar_id]


def record_verification_success(avatar_id: str) -> None:
    """Reset consecutive failure count after a successful verification."""
    _drift_fail_counts.pop(avatar_id, None)


def should_drift_trigger_refresh(avatar_id: str) -> bool:
    """Return True if the avatar has enough consecutive failures for immediate refresh."""
    return _drift_fail_counts.get(avatar_id, 0) >= _DRIFT_FAIL_THRESHOLD


def refresh_canonical_references(
    db: Any = None,
    staleness_policy: bool = True,
) -> dict[str, Any]:
    """Refresh canonical reference frames for all avatars with recent renders.

    Phase 2.2: When ``staleness_policy=True`` (default), only refresh when:
    1. The existing canonical frame is older than ``CANONICAL_MAX_AGE_DAYS``, OR
    2. A drift-triggered refresh has been flagged (≥3 consecutive failures).

    Can be called directly (synchronous) or via Celery beat schedule.
    Returns a summary dict with ``avatars_refreshed`` count.
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
    drift_triggered = 0
    try:
        from app.models.autovis import AvatarVisualDna
        avatar_ids = list({row.avatar_id for row in db.query(AvatarVisualDna).all()})
        refresher = CanonicalReferenceRefresher()
        extractor = MediaEmbeddingExtractor()

        for avatar_id in avatar_ids:
            try:
                drift_needed = should_drift_trigger_refresh(avatar_id)
                if staleness_policy and not drift_needed:
                    # Check if canonical frame is stale
                    if not _is_canonical_stale(db, avatar_id):
                        skipped += 1
                        logger.debug(
                            "canonical_reference_scheduler: canonical not stale for avatar=%s, skipping",
                            avatar_id,
                        )
                        continue

                render_frames = _collect_render_frames(db, avatar_id, extractor)
                if not render_frames:
                    skipped += 1
                    logger.debug(
                        "canonical_reference_scheduler: no render frames for avatar=%s, skipping",
                        avatar_id,
                    )
                    continue

                refresher.refresh_after_success(db, avatar_id, render_frames)
                refreshed += 1
                if drift_needed:
                    drift_triggered += 1
                    # Reset failure counter after refresh
                    record_verification_success(avatar_id)
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
        "canonical_reference_scheduler: refreshed=%d skipped=%d drift_triggered=%d",
        refreshed,
        skipped,
        drift_triggered,
    )
    return {
        "avatars_refreshed": refreshed,
        "avatars_skipped": skipped,
        "drift_triggered_refreshes": drift_triggered,
    }


def force_refresh_avatar_canonical(db: Any, avatar_id: str) -> dict[str, Any]:
    """Force immediate canonical refresh for a single avatar (on-demand API).

    Phase 2.2: Used by POST /api/v1/avatar/{id}/canonical/refresh.
    """
    from app.services.avatar.avatar_identity_service import CanonicalReferenceRefresher
    from app.services.avatar.media_embedding_extractor import MediaEmbeddingExtractor

    extractor = MediaEmbeddingExtractor()
    render_frames = _collect_render_frames(db, avatar_id, extractor)
    if not render_frames:
        return {
            "ok": False,
            "avatar_id": avatar_id,
            "message": "No render frames available for refresh.",
        }
    refresher = CanonicalReferenceRefresher()
    refresher.refresh_after_success(db, avatar_id, render_frames)
    record_verification_success(avatar_id)
    return {"ok": True, "avatar_id": avatar_id, "frames_used": len(render_frames)}


def _is_canonical_stale(db: Any, avatar_id: str) -> bool:
    """Return True if the canonical frame is older than _CANONICAL_MAX_AGE_DAYS."""
    try:
        from app.models.autovis import AvatarReferenceFrame

        frame = (
            db.query(AvatarReferenceFrame)
            .filter(AvatarReferenceFrame.avatar_id == avatar_id)
            .order_by(AvatarReferenceFrame.created_at.desc())
            .first()
        )
        if frame is None:
            return True  # No canonical frame exists → stale
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
            days=_CANONICAL_MAX_AGE_DAYS
        )
        created = frame.created_at
        if created is None:
            return True
        return created < cutoff
    except Exception:
        return True  # Fail open: treat as stale


def _collect_render_frames(
    db: Any,
    avatar_id: str,
    extractor: "MediaEmbeddingExtractor",
) -> list[list[float]]:
    """Return up to ``_TOP_N_FRAMES`` per-frame embeddings from real render outputs."""
    render_urls: list[str] = _find_recent_render_urls(db, avatar_id)
    if not render_urls:
        return []

    frames: list[list[float]] = []
    for url in render_urls[:_TOP_N_FRAMES]:
        try:
            emb = extractor.extract(url, n_frames=1)
            frames.append(emb)
        except Exception as exc:
            logger.debug(
                "canonical_reference_scheduler: extraction failed url=%s avatar=%s: %s",
                url, avatar_id, exc,
            )
    return frames


def _find_recent_render_urls(db: Any, avatar_id: str) -> list[str]:
    """Return output URLs of recently completed renders for an avatar."""
    try:
        from app.models.render_job import RenderJob  # type: ignore[import]

        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
        rows = (
            db.query(RenderJob)
            .filter(
                RenderJob.status == "completed",
                RenderJob.updated_at >= cutoff,
            )
            .order_by(RenderJob.updated_at.desc())
            .limit(_TOP_N_FRAMES * 3)
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

