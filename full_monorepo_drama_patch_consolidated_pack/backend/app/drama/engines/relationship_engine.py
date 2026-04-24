from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class RelationshipSnapshot:
    source_character_id: str
    target_character_id: str
    relation_type: Optional[str]
    trust_level: float
    dependence_level: float
    resentment_level: float
    attraction_level: float
    rivalry_level: float
    dominance_source_over_target: float
    hidden_agenda_score: float
    unresolved_tension_score: float


class RelationshipEngine:
    """Creates normalized, engine-friendly views over directional relationship edges."""

    def to_snapshot(self, edge: Any) -> RelationshipSnapshot:
        return RelationshipSnapshot(
            source_character_id=str(edge.source_character_id),
            target_character_id=str(edge.target_character_id),
            relation_type=getattr(edge, "relation_type", None),
            trust_level=float(getattr(edge, "trust_level", 0.0) or 0.0),
            dependence_level=float(getattr(edge, "dependence_level", 0.0) or 0.0),
            resentment_level=float(getattr(edge, "resentment_level", 0.0) or 0.0),
            attraction_level=float(getattr(edge, "attraction_level", 0.0) or 0.0),
            rivalry_level=float(getattr(edge, "rivalry_level", 0.0) or 0.0),
            dominance_source_over_target=float(getattr(edge, "dominance_source_over_target", 0.0) or 0.0),
            hidden_agenda_score=float(getattr(edge, "hidden_agenda_score", 0.0) or 0.0),
            unresolved_tension_score=float(getattr(edge, "unresolved_tension_score", 0.0) or 0.0),
        )

    def build_graph_index(self, edges: Iterable[Any]) -> Dict[str, Dict[str, RelationshipSnapshot]]:
        index: Dict[str, Dict[str, RelationshipSnapshot]] = {}
        for edge in edges:
            snap = self.to_snapshot(edge)
            index.setdefault(snap.source_character_id, {})[snap.target_character_id] = snap
        return index

    def pairwise_view(
        self,
        graph_index: Dict[str, Dict[str, RelationshipSnapshot]],
        source_id: str,
        target_id: str,
    ) -> Dict[str, Optional[RelationshipSnapshot]]:
        return {
            "forward": graph_index.get(source_id, {}).get(target_id),
            "reverse": graph_index.get(target_id, {}).get(source_id),
        }
