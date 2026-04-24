from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.drama.schemas.relationship import (
    RelationshipCreate,
    RelationshipRead,
    RelationshipUpdate,
)
from app.drama.services.relationship_service import RelationshipService

router = APIRouter(prefix="/api/v1/drama/relationships", tags=["drama_relationships"])


@router.get("", response_model=List[RelationshipRead])
def list_relationships(
    project_id: Optional[UUID] = Query(default=None),
    character_id: Optional[UUID] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[RelationshipRead]:
    service = RelationshipService(db)
    if project_id:
        return service.list_for_project(project_id)
    if character_id:
        return service.list_for_character(character_id)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Provide project_id or character_id.",
    )


@router.post("", response_model=RelationshipRead, status_code=status.HTTP_201_CREATED)
def create_relationship(
    payload: RelationshipCreate,
    db: Session = Depends(get_db),
) -> RelationshipRead:
    return RelationshipService(db).create(payload)


@router.patch("/{relationship_id}", response_model=RelationshipRead)
def update_relationship(
    relationship_id: UUID,
    payload: RelationshipUpdate,
    db: Session = Depends(get_db),
) -> RelationshipRead:
    updated = RelationshipService(db).update(relationship_id, payload)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found.")
    return updated


@router.post("/graph/rebuild")
def rebuild_relationship_graph(
    project_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    # TODO: wire to RelationshipEngine.rebuild_graph(project_id)
    existing = RelationshipService(db).list_for_project(project_id)
    return {
        "project_id": str(project_id),
        "status": "stubbed",
        "edge_count": len(existing),
        "message": "Phase 2 skeleton route ready for relationship graph rebuild.",
    }
