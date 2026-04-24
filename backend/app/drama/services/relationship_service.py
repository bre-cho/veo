from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.drama.models.drama_relationship_edge import DramaRelationshipEdge
from app.drama.schemas.relationship import (
    RelationshipCreate,
    RelationshipRead,
    RelationshipUpdate,
)


class RelationshipService:
    """Persistence/service layer for directional relationship edges.

    Notes:
    - This intentionally avoids smart orchestration. Phase 2 engines should call this
      after computing deltas.
    - Edge A->B is independent from B->A.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_project(self, project_id: UUID) -> List[DramaRelationshipEdge]:
        return (
            self.db.query(DramaRelationshipEdge)
            .filter(DramaRelationshipEdge.project_id == str(project_id))
            .all()
        )

    def list_for_character(self, character_id: UUID) -> List[DramaRelationshipEdge]:
        return (
            self.db.query(DramaRelationshipEdge)
            .filter(DramaRelationshipEdge.source_character_id == character_id)
            .all()
        )

    def get(self, relationship_id: UUID) -> Optional[DramaRelationshipEdge]:
        return self.db.query(DramaRelationshipEdge).get(relationship_id)

    def create(self, payload: RelationshipCreate) -> DramaRelationshipEdge:
        edge = DramaRelationshipEdge(**payload.model_dump())
        self.db.add(edge)
        self.db.commit()
        self.db.refresh(edge)
        return edge

    def update(
        self,
        relationship_id: UUID,
        payload: RelationshipUpdate,
    ) -> Optional[DramaRelationshipEdge]:
        edge = self.get(relationship_id)
        if not edge:
            return None

        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(edge, key, value)

        self.db.add(edge)
        self.db.commit()
        self.db.refresh(edge)
        return edge

    def upsert_directional_edge(
        self,
        project_id: UUID,
        source_character_id: UUID,
        target_character_id: UUID,
        defaults: dict,
    ) -> DramaRelationshipEdge:
        edge = (
            self.db.query(DramaRelationshipEdge)
            .filter(DramaRelationshipEdge.project_id == str(project_id))
            .filter(DramaRelationshipEdge.source_character_id == source_character_id)
            .filter(DramaRelationshipEdge.target_character_id == target_character_id)
            .one_or_none()
        )

        if edge is None:
            edge = DramaRelationshipEdge(
                project_id=str(project_id),
                source_character_id=source_character_id,
                target_character_id=target_character_id,
                **defaults,
            )
        else:
            for key, value in defaults.items():
                setattr(edge, key, value)

        self.db.add(edge)
        self.db.commit()
        self.db.refresh(edge)
        return edge
