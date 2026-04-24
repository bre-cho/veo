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
from app.drama.engines.relationship_engine import RelationshipEngine
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
    service = RelationshipService(db)
    engine = RelationshipEngine()
    existing = service.list_for_project(project_id)
    graph_index = engine.build_graph_index(existing)
    node_ids: set[str] = set()
    for source_id, targets in graph_index.items():
        node_ids.add(source_id)
        node_ids.update(targets.keys())
    edges_serialized = [
        {
            "source_character_id": snap.source_character_id,
            "target_character_id": snap.target_character_id,
            "relation_type": snap.relation_type,
            "trust_level": snap.trust_level,
            "dependence_level": snap.dependence_level,
            "resentment_level": snap.resentment_level,
            "attraction_level": snap.attraction_level,
            "rivalry_level": snap.rivalry_level,
            "dominance_source_over_target": snap.dominance_source_over_target,
            "hidden_agenda_score": snap.hidden_agenda_score,
            "unresolved_tension_score": snap.unresolved_tension_score,
        }
        for targets in graph_index.values()
        for snap in targets.values()
    ]
    return {
        "project_id": str(project_id),
        "status": "rebuilt",
        "node_count": len(node_ids),
        "edge_count": len(existing),
        "nodes": [{"character_id": node_id} for node_id in sorted(node_ids)],
        "edges": edges_serialized,
    }


@router.get("/graph")
def get_relationship_graph(
    project_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    service = RelationshipService(db)
    edges = service.list_for_project(project_id)
    node_ids = set()
    for edge in edges:
        node_ids.add(str(edge.source_character_id))
        node_ids.add(str(edge.target_character_id))
    return {
        "project_id": str(project_id),
        "nodes": [{"character_id": node_id} for node_id in sorted(node_ids)],
        "edges": [RelationshipRead.model_validate(edge).model_dump() for edge in edges],
    }
