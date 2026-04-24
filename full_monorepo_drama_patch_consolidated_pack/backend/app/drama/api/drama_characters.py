from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.drama.schemas.character import (
    CharacterCreate,
    CharacterRead,
    CharacterStateRead,
    CharacterUpdate,
    CharacterWithStateRead,
)
from app.drama.services.cast_service import CastService

try:
    from app.api import deps
except Exception:  # pragma: no cover
    deps = None


router = APIRouter()


def get_db_fallback() -> Session:  # pragma: no cover
    raise RuntimeError("Wire your repo Session dependency here: app.api.deps.get_db")


DBSession = Annotated[Session, Depends(deps.get_db if deps else get_db_fallback)]


@router.get("", response_model=list[CharacterRead])
def list_drama_characters(
    project_id: Annotated[str, Query(min_length=1, max_length=128)],
    db: DBSession,
) -> list[CharacterRead]:
    service = CastService(db)
    return service.list_characters(project_id=project_id)


@router.post("", response_model=CharacterRead, status_code=status.HTTP_201_CREATED)
def create_drama_character(payload: CharacterCreate, db: DBSession) -> CharacterRead:
    service = CastService(db)
    return service.create_character(payload)


@router.get("/{character_id}", response_model=CharacterWithStateRead)
def get_drama_character(character_id: UUID, db: DBSession) -> CharacterWithStateRead:
    service = CastService(db)
    profile = service.get_character(character_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drama character not found")
    latest_state = service.get_latest_state(character_id)
    return CharacterWithStateRead(character=profile, latest_state=latest_state)


@router.patch("/{character_id}", response_model=CharacterRead)
def update_drama_character(
    character_id: UUID,
    payload: CharacterUpdate,
    db: DBSession,
) -> CharacterRead:
    service = CastService(db)
    profile = service.update_character(character_id, payload)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drama character not found")
    return profile


@router.post("/{character_id}/preset/apply", response_model=CharacterRead)
def apply_archetype_preset(
    character_id: UUID,
    archetype_name: Annotated[str, Query(min_length=1, max_length=100)],
    db: DBSession,
) -> CharacterRead:
    service = CastService(db)
    profile = service.apply_archetype_preset(character_id=character_id, archetype_name=archetype_name)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drama character not found")
    return profile


@router.get("/{character_id}/state/latest", response_model=CharacterStateRead)
def get_latest_drama_state(character_id: UUID, db: DBSession) -> CharacterStateRead:
    service = CastService(db)
    state = service.get_latest_state(character_id)
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drama state not found")
    return state
