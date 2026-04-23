"""avatar_memory_engine — fetches relevant episodic memory traces for a scene.

Memory traces are keyed by ``continuity_tag``.  The engine surfaces traces
whose tags match the current beat's ``memory_trigger``, sorted by emotional
weight descending.  When no DB session is available the in-process store is
used (useful for tests and low-dependency callers).
"""
from __future__ import annotations

from typing import Any


class AvatarMemoryEngine:
    """Fetches emotionally relevant memory traces for an avatar.

    Supports both an in-process fallback store and SQLAlchemy DB lookups.
    """

    def __init__(self) -> None:
        # In-process store: avatar_id → list of memory trace dicts
        self._memory_store: dict[str, list[dict[str, Any]]] = {}

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def record(
        self,
        db: Any | None,
        *,
        avatar_id: str,
        memory_type: str = "event",
        trigger: str,
        emotional_weight: float = 0.5,
        narrative_summary: str,
        continuity_tag: str | None = None,
        source_scene_index: int | None = None,
        source_series_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Persist a new memory trace.

        Writes to DB when available; always keeps an in-process copy.
        """
        trace: dict[str, Any] = {
            "avatar_id": avatar_id,
            "memory_type": memory_type,
            "trigger": trigger,
            "emotional_weight": emotional_weight,
            "narrative_summary": narrative_summary,
            "continuity_tag": continuity_tag,
            "source_scene_index": source_scene_index,
            "source_series_id": source_series_id,
            "metadata": metadata or {},
        }

        # In-process cache
        self._memory_store.setdefault(avatar_id, []).append(trace)

        # DB persistence
        if db is not None:
            try:
                from app.models.avatar_memory_trace import AvatarMemoryTrace

                row = AvatarMemoryTrace(
                    avatar_id=avatar_id,
                    memory_type=memory_type,
                    trigger=trigger,
                    emotional_weight=emotional_weight,
                    narrative_summary=narrative_summary,
                    continuity_tag=continuity_tag,
                    source_scene_index=source_scene_index,
                    source_series_id=source_series_id,
                    metadata_json=metadata or {},
                )
                db.add(row)
                db.commit()
            except Exception:
                pass  # memory persistence is non-fatal

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def fetch_relevant(
        self,
        avatar_id: str,
        trigger_tag: str | None,
        db: Any | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Return memory traces relevant to *trigger_tag*, sorted by emotional weight.

        Checks DB first, falls back to in-process store.
        """
        if trigger_tag is None:
            return []

        traces: list[dict[str, Any]] = []

        if db is not None:
            try:
                from app.models.avatar_memory_trace import AvatarMemoryTrace

                rows = (
                    db.query(AvatarMemoryTrace)
                    .filter(
                        AvatarMemoryTrace.avatar_id == avatar_id,
                        AvatarMemoryTrace.continuity_tag == trigger_tag,
                    )
                    .order_by(AvatarMemoryTrace.emotional_weight.desc())
                    .limit(limit)
                    .all()
                )
                traces = [
                    {
                        "avatar_id": r.avatar_id,
                        "memory_type": r.memory_type,
                        "trigger": r.trigger,
                        "emotional_weight": r.emotional_weight,
                        "narrative_summary": r.narrative_summary,
                        "continuity_tag": r.continuity_tag,
                    }
                    for r in rows
                ]
            except Exception:
                pass

        # Supplement / fallback with in-process store
        if not traces:
            in_proc = self._memory_store.get(avatar_id, [])
            traces = [m for m in in_proc if m.get("continuity_tag") == trigger_tag]
            traces.sort(key=lambda m: float(m.get("emotional_weight") or 0), reverse=True)
            traces = traces[:limit]

        return traces
