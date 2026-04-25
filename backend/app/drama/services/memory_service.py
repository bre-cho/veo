from __future__ import annotations

from typing import Iterable, Sequence
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.drama.models.memory_trace import DramaMemoryTrace


def _to_uuid(value) -> UUID | None:
    return UUID(str(value)) if value else None

class DramaMemoryService:
    """Persistence layer for character memory traces.

    Notes:
    - Side effects are explicit and scene-scoped.
    - Retrieval sorts by persistence and freshness to support recall.
    - Heuristics are intentionally simple for phase 4; can be upgraded to learned ranking later.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_trace(self, payload: dict) -> DramaMemoryTrace:
        trace = DramaMemoryTrace(**payload)
        self.db.add(trace)
        self.db.flush()
        return trace

    def bulk_create_traces(self, payloads: Iterable[dict]) -> list[DramaMemoryTrace]:
        traces: list[DramaMemoryTrace] = []
        for payload in payloads:
            trace = DramaMemoryTrace(**payload)
            self.db.add(trace)
            traces.append(trace)
        self.db.flush()
        return traces

    def list_for_character(
        self,
        character_id: UUID,
        *,
        related_character_id: UUID | None = None,
        limit: int = 20,
    ) -> Sequence[DramaMemoryTrace]:
        stmt = select(DramaMemoryTrace).where(DramaMemoryTrace.character_id == character_id)
        if related_character_id:
            stmt = stmt.where(DramaMemoryTrace.related_character_id == related_character_id)
        stmt = stmt.order_by(desc(DramaMemoryTrace.persistence_score), desc(DramaMemoryTrace.created_at)).limit(limit)
        return self.db.execute(stmt).scalars().all()

    # Compatibility surface for earlier API drafts.
    def list_memories(
        self,
        *,
        character_id: UUID,
        related_character_id: UUID | None = None,
        min_persistence_score: float | None = None,
        limit: int = 20,
    ) -> Sequence[DramaMemoryTrace]:
        stmt = select(DramaMemoryTrace).where(DramaMemoryTrace.character_id == character_id)
        if related_character_id is not None:
            stmt = stmt.where(DramaMemoryTrace.related_character_id == related_character_id)
        if min_persistence_score is not None:
            stmt = stmt.where(DramaMemoryTrace.persistence_score >= min_persistence_score)
        stmt = stmt.order_by(desc(DramaMemoryTrace.persistence_score), desc(DramaMemoryTrace.created_at)).limit(limit)
        return self.db.execute(stmt).scalars().all()

    def get_memory(self, memory_id: UUID) -> DramaMemoryTrace | None:
        stmt = select(DramaMemoryTrace).where(DramaMemoryTrace.id == memory_id).limit(1)
        return self.db.execute(stmt).scalar_one_or_none()

    def build_scene_memory_payloads(self, scene_id: UUID, analysis: dict) -> list[dict]:
        payloads: list[dict] = []
        relationship_shifts = analysis.get("relationship_shifts", [])
        outcome = analysis.get("drama_state", {})
        for shift in relationship_shifts:
            source_id = shift.get("source")
            target_id = shift.get("target")
            if not source_id:
                continue
            emotional_weight = abs(float(shift.get("trust_delta", 0.0))) + abs(float(shift.get("resentment_delta", 0.0)))
            payloads.append(
                {
                    "project_id": _to_uuid(analysis.get("project_id")),
                    "episode_id": _to_uuid(analysis.get("episode_id")),
                    "character_id": _to_uuid(source_id),
                    "related_character_id": _to_uuid(target_id),
                    "source_scene_id": scene_id,
                    "event_type": outcome.get("outcome_type", "scene_shift"),
                    "meaning_label": outcome.get("turning_point") or "scene_shift",
                    "recall_trigger": (
                        analysis.get("scene_context", {}).get("visible_conflict")
                        or analysis.get("scene_context", {}).get("hidden_conflict")
                        or outcome.get("outcome_type")
                        or "scene_shift"
                    ),
                    "emotional_weight": emotional_weight,
                    "trust_impact": float(shift.get("trust_delta", 0.0)),
                    "shame_impact": float(shift.get("shame_delta", 0.0)),
                    "fear_impact": float(shift.get("fear_delta", 0.0)),
                    "dominance_impact": float(shift.get("dominance_delta", 0.0)),
                    "persistence_score": min(1.0, 0.35 + emotional_weight),
                    "decay_rate": 0.05 if emotional_weight > 0.25 else 0.1,
                    "notes": "Auto-generated from scene analysis.",
                }
            )
        return payloads


class MemoryService(DramaMemoryService):
    """Backward-compatible alias used by current API routers."""

    pass
