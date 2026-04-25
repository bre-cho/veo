"""factory_memory – DNA / learning memory system for the factory pipeline.

After each run completes (or at key milestones) the orchestrator writes
FactoryMemoryEvent rows.  Future runs load relevant memory blobs via
``load_recent_memory``.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.factory_run import FactoryMemoryEvent

logger = logging.getLogger(__name__)

MEMORY_TYPES = [
    "topic_dna",
    "script_dna",
    "scene_dna",
    "avatar_dna",
    "render_dna",
    "seo_dna",
    "performance_dna",
    "failure_dna",
    "winner_dna",
]


def record_memory(
    db: Session,
    run_id: str,
    memory_type: str,
    payload: dict[str, Any],
) -> FactoryMemoryEvent:
    """Persist a memory blob for the given run and type."""
    now = datetime.now(timezone.utc)
    event = FactoryMemoryEvent(
        run_id=run_id,
        memory_type=memory_type,
        payload_json=json.dumps(payload),
        recorded_at=now,
    )
    db.add(event)
    db.commit()
    logger.debug("Memory recorded: run=%s type=%s", run_id, memory_type)
    return event


def load_recent_memory(
    db: Session,
    memory_type: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Return the *limit* most recent memory blobs of the given type."""
    rows = (
        db.query(FactoryMemoryEvent)
        .filter(FactoryMemoryEvent.memory_type == memory_type)
        .order_by(FactoryMemoryEvent.recorded_at.desc())
        .limit(limit)
        .all()
    )
    results: list[dict[str, Any]] = []
    for row in rows:
        try:
            results.append(json.loads(row.payload_json or "{}"))
        except (json.JSONDecodeError, TypeError):
            results.append({})
    return results
