"""WinningSceneGraphStore — persist and retrieve winning storyboard scene graphs.

Phase 4.4: Records high-converting scene graphs (dependency_graph snapshots)
and exposes top-N retrieval for seeding new storyboard generation.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

_SCORE_THRESHOLD_HIGH = float(os.environ.get("WINNING_GRAPH_SCORE_THRESHOLD", "0.70"))
# In-memory store for use without DB
_IN_MEMORY_STORE: list[dict[str, Any]] = []


class WinningSceneGraphStore:
    """Store and retrieve winning scene graph snapshots.

    Storage is backed by a DB table ``winning_scene_graphs`` when a SQLAlchemy
    session is provided, otherwise uses an in-memory list (useful for tests
    and environments without a DB).
    """

    def __init__(self, db: Any | None = None) -> None:
        self._db = db

    def record_winning_graph(
        self,
        storyboard_id: str,
        platform: str | None,
        conversion_score: float,
        scene_sequence: list[dict[str, Any]] | None = None,
        dependency_graph: dict[str, Any] | None = None,
    ) -> bool:
        """Persist a storyboard's scene graph when conversion_score > threshold.

        Returns True if the graph was persisted, False if below threshold.
        """
        if conversion_score < _SCORE_THRESHOLD_HIGH:
            return False

        record = {
            "storyboard_id": storyboard_id,
            "platform": platform or "",
            "conversion_score": round(conversion_score, 4),
            "scene_sequence": scene_sequence or [],
            "dependency_graph": dependency_graph or {},
            "recorded_at": time.time(),
        }

        if self._db is not None:
            try:
                return self._db_record(record)
            except Exception as exc:
                logger.warning("WinningSceneGraphStore._db_record failed: %s", exc)

        # Fall back to in-memory
        _IN_MEMORY_STORE.append(record)
        return True

    def get_top_graphs(
        self,
        platform: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Return top-N winning scene graphs sorted by conversion_score desc.

        Filters by ``platform`` when specified.
        """
        if self._db is not None:
            try:
                return self._db_get_top(platform=platform, limit=limit)
            except Exception as exc:
                logger.warning("WinningSceneGraphStore._db_get_top failed: %s", exc)

        # In-memory fallback
        records = _IN_MEMORY_STORE
        if platform:
            records = [r for r in records if r.get("platform") == platform]
        records = sorted(records, key=lambda r: r.get("conversion_score", 0), reverse=True)
        return records[:limit]

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def _db_record(self, record: dict[str, Any]) -> bool:
        """Insert a winning graph record into the DB."""
        from app.models.winning_scene_graph import WinningSceneGraph  # type: ignore[import]
        from datetime import datetime, timezone

        row = WinningSceneGraph(
            storyboard_id=record["storyboard_id"],
            platform=record["platform"],
            conversion_score=record["conversion_score"],
            scene_sequence=record["scene_sequence"],
            dependency_graph=record["dependency_graph"],
            recorded_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self._db.add(row)
        self._db.commit()
        return True

    def _db_get_top(
        self, platform: str | None, limit: int
    ) -> list[dict[str, Any]]:
        """Retrieve top graphs from the DB."""
        from app.models.winning_scene_graph import WinningSceneGraph  # type: ignore[import]

        query = self._db.query(WinningSceneGraph)
        if platform:
            query = query.filter(WinningSceneGraph.platform == platform)
        rows = (
            query.order_by(WinningSceneGraph.conversion_score.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "storyboard_id": row.storyboard_id,
                "platform": row.platform,
                "conversion_score": row.conversion_score,
                "scene_sequence": row.scene_sequence or [],
                "dependency_graph": row.dependency_graph or {},
                "recorded_at": row.recorded_at.timestamp() if row.recorded_at else None,
            }
            for row in rows
        ]
