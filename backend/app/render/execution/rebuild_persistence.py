"""DB-backed persistence adapters for ApprovedRebuildExecutor.

Provides:
* ``DbRebuildPersistence`` – callable-compatible audit store and idempotency
  backend that write to the ``render_rebuild_audit_logs`` and
  ``render_rebuild_idempotency_keys`` PostgreSQL tables.

Usage in the API layer::

    from app.db.session import SessionLocal
    from app.render.execution.rebuild_persistence import DbRebuildPersistence

    db = SessionLocal()
    persistence = DbRebuildPersistence(db)
    executor = ApprovedRebuildExecutor(
        rebuild_fn=...,
        audit_store=persistence.append_audit,
        idempotency_backend=persistence,
    )
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

_logger = logging.getLogger(__name__)


class DbRebuildPersistence:
    """Wraps a SQLAlchemy session to provide audit and idempotency storage."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Audit store – passed as callable to ApprovedRebuildExecutor
    # ------------------------------------------------------------------

    def append_audit(self, entry: Dict[str, Any]) -> None:
        """Persist one audit entry to ``render_rebuild_audit_logs``."""
        from app.models.render_rebuild_audit_log import RenderRebuildAuditLog  # lazy

        extras = {
            k: v
            for k, v in entry.items()
            if k not in {
                "job_id",
                "event",
                "project_id",
                "episode_id",
                "changed_scene_id",
                "selected_strategy",
                "timestamp",
            }
        }
        row = RenderRebuildAuditLog(
            id=str(uuid.uuid4()),
            job_id=entry.get("job_id", ""),
            event=entry.get("event", ""),
            project_id=entry.get("project_id"),
            episode_id=entry.get("episode_id"),
            changed_scene_id=entry.get("changed_scene_id"),
            selected_strategy=entry.get("selected_strategy"),
            extras_json=json.dumps(extras) if extras else None,
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        try:
            self._db.add(row)
            self._db.commit()
        except Exception as exc:  # noqa: BLE001
            _logger.warning("Failed to persist audit log entry: %s", exc)
            self._db.rollback()

    # ------------------------------------------------------------------
    # Idempotency backend – atomic reserve / complete pattern
    # ------------------------------------------------------------------

    def reserve_key(self, key: str, job_id: str) -> bool:
        """Atomically insert a row with status ``executing``.

        Returns ``True`` if the row was inserted (key was unclaimed).
        Returns ``False`` if the key already exists (duplicate / concurrent
        request) — the caller should fetch the existing result via ``check()``.
        """
        from app.models.render_rebuild_idempotency_key import RenderRebuildIdempotencyKey  # lazy

        row = RenderRebuildIdempotencyKey(
            idempotency_key=key,
            job_id=job_id,
            status="executing",
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        try:
            self._db.add(row)
            self._db.commit()
            return True
        except IntegrityError:
            self._db.rollback()
            return False
        except Exception as exc:  # noqa: BLE001
            _logger.warning("reserve_key failed for key %s: %s", key, exc)
            self._db.rollback()
            return False

    def complete_key(self, key: str, result: Dict[str, Any]) -> None:
        """Update the reserved row to its final status and result payload."""
        from app.models.render_rebuild_idempotency_key import RenderRebuildIdempotencyKey  # lazy

        try:
            row = (
                self._db.query(RenderRebuildIdempotencyKey)
                .filter(RenderRebuildIdempotencyKey.idempotency_key == key)
                .first()
            )
            if row is not None:
                row.status = result.get("status", "unknown")
                row.result_json = json.dumps(result)
            self._db.commit()
        except Exception as exc:  # noqa: BLE001
            _logger.warning("complete_key failed for key %s: %s", key, exc)
            self._db.rollback()

    # ------------------------------------------------------------------
    # Idempotency backend – check() / store() (legacy / fallback)
    # ------------------------------------------------------------------

    def check(self, key: str) -> Optional[Dict[str, Any]]:
        """Return the cached execution result for *key*, or ``None``."""
        from app.models.render_rebuild_idempotency_key import RenderRebuildIdempotencyKey  # lazy

        try:
            row = (
                self._db.query(RenderRebuildIdempotencyKey)
                .filter(RenderRebuildIdempotencyKey.idempotency_key == key)
                .first()
            )
            if row is None:
                return None
            if row.result_json:
                return json.loads(row.result_json)
            return {"job_id": row.job_id, "status": row.status}
        except Exception as exc:  # noqa: BLE001
            _logger.warning("Idempotency check failed for key %s: %s", key, exc)
            return None

    def store(self, key: str, result: Dict[str, Any]) -> None:
        """Persist an idempotency entry for *key*."""
        from app.models.render_rebuild_idempotency_key import RenderRebuildIdempotencyKey  # lazy

        try:
            existing = (
                self._db.query(RenderRebuildIdempotencyKey)
                .filter(RenderRebuildIdempotencyKey.idempotency_key == key)
                .first()
            )
            if existing is not None:
                existing.status = result.get("status", "unknown")
                existing.result_json = json.dumps(result)
            else:
                row = RenderRebuildIdempotencyKey(
                    idempotency_key=key,
                    job_id=result.get("job_id", ""),
                    status=result.get("status", "unknown"),
                    result_json=json.dumps(result),
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
                self._db.add(row)
            self._db.commit()
        except Exception as exc:  # noqa: BLE001
            _logger.warning("Idempotency store failed for key %s: %s", key, exc)
            self._db.rollback()

    def get_audit_trail(self, job_id: str) -> list[Dict[str, Any]]:
        """Return all audit entries for *job_id* from the DB."""
        from app.models.render_rebuild_audit_log import RenderRebuildAuditLog  # lazy

        try:
            rows = (
                self._db.query(RenderRebuildAuditLog)
                .filter(RenderRebuildAuditLog.job_id == job_id)
                .order_by(RenderRebuildAuditLog.timestamp)
                .all()
            )
            result = []
            for row in rows:
                entry: Dict[str, Any] = {
                    "job_id": row.job_id,
                    "event": row.event,
                    "project_id": row.project_id,
                    "episode_id": row.episode_id,
                    "changed_scene_id": row.changed_scene_id,
                    "selected_strategy": row.selected_strategy,
                    "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                }
                if row.extras_json:
                    try:
                        entry.update(json.loads(row.extras_json))
                    except Exception:  # noqa: BLE001
                        pass
                result.append(entry)
            return result
        except Exception as exc:  # noqa: BLE001
            _logger.warning("Failed to fetch audit trail for job %s: %s", job_id, exc)
            return []
