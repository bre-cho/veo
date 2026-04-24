from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.drama.schemas.drama_memory import DramaMemoryTraceRead
from app.drama.services.memory_service import MemoryService
from app.drama.engines.memory_recall_engine import MemoryRecallEngine

router = APIRouter(prefix="/api/v1/drama/memory", tags=["drama-memory"])


@router.get("/characters/{character_id}", response_model=List[DramaMemoryTraceRead])
def list_character_memories(
    character_id: UUID,
    related_character_id: Optional[UUID] = Query(default=None),
    min_persistence_score: Optional[float] = Query(default=None, ge=0.0, le=1.0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    service = MemoryService(db)
    return service.list_memories(
        character_id=character_id,
        related_character_id=related_character_id,
        min_persistence_score=min_persistence_score,
        limit=limit,
    )


@router.get("/characters/{character_id}/recall", response_model=List[DramaMemoryTraceRead])
def recall_character_memories(
    character_id: UUID,
    trigger: str = Query(..., min_length=1),
    related_character_id: Optional[UUID] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    service = MemoryService(db)
    memories = service.list_memories(
        character_id=character_id,
        related_character_id=related_character_id,
        limit=200,
    )
    engine = MemoryRecallEngine()
    recalled = engine.recall(memories=memories, trigger=trigger, limit=limit)
    return recalled


@router.get("/{memory_id}", response_model=DramaMemoryTraceRead)
def get_memory(memory_id: UUID, db: Session = Depends(get_db)):
    service = MemoryService(db)
    memory = service.get_memory(memory_id)
    if memory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drama memory not found")
    return memory
