from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.drama.engines.character_intent_engine import CharacterIntentEngine
from app.drama.engines.power_shift_engine import PowerShiftEngine
from app.drama.engines.relationship_engine import RelationshipEngine
from app.drama.engines.subtext_engine import SubtextEngine
from app.drama.engines.tension_engine import TensionEngine
from app.drama.models.drama_character_profile import DramaCharacterProfile
from app.drama.models.drama_relationship_edge import DramaRelationshipEdge


class SceneDramaService:
    """Orchestrates phase-2 scene analysis without persisting scene states yet.

    This service is deliberately read-heavy and side-effect light so teams can merge and
    verify the analysis path before wiring DB tables/workers.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.intent_engine = CharacterIntentEngine()
        self.relationship_engine = RelationshipEngine()
        self.tension_engine = TensionEngine()
        self.subtext_engine = SubtextEngine()
        self.power_shift_engine = PowerShiftEngine()

    def _load_profiles(self, character_ids: List[UUID]) -> List[DramaCharacterProfile]:
        return (
            self.db.query(DramaCharacterProfile)
            .filter(DramaCharacterProfile.id.in_(character_ids))
            .all()
        )

    def _load_edges(self, project_id: UUID, character_ids: List[UUID]) -> List[DramaRelationshipEdge]:
        return (
            self.db.query(DramaRelationshipEdge)
            .filter(DramaRelationshipEdge.project_id == project_id)
            .filter(DramaRelationshipEdge.source_character_id.in_(character_ids))
            .filter(DramaRelationshipEdge.target_character_id.in_(character_ids))
            .all()
        )

    def analyze_scene(
        self,
        project_id: UUID,
        scene_id: UUID,
        character_ids: List[UUID],
        scene_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        scene_context = scene_context or {}
        profiles = self._load_profiles(character_ids)
        edges = self._load_edges(project_id, character_ids)
        graph_index = self.relationship_engine.build_graph_index(edges)

        intents = [self.intent_engine.derive(profile, scene_context) for profile in profiles]
        tension = self.tension_engine.score(intents, graph_indexed_edges(graph_index), scene_context)

        subtext_map: List[Dict[str, Any]] = []
        for speaker in profiles:
            for target in profiles:
                if speaker.id == target.id:
                    continue
                forward = graph_index.get(str(speaker.id), {}).get(str(target.id))
                subtext_map.append(
                    self.subtext_engine.infer_dialogue_actions(
                        speaker_profile=speaker,
                        target_profile=target,
                        relationship_forward=forward,
                        scene_context=scene_context,
                    )
                )

        power_shift = self.power_shift_engine.compute(scene_context, graph_indexed_edges(graph_index))

        dominant_character_id = infer_dominant_character(graph_index)

        drama_state = {
            "tension_score": tension.get("tension_score", 0.0),
            "pressure_level": tension.get("tension_score", 0.0),
            "dominant_character_id": dominant_character_id,
            "outcome_type": scene_context.get("outcome_type", "scene_shift"),
            "turning_point": scene_context.get("turning_point"),
            "power_shift_delta": power_shift.get("total_delta", 0.0),
            "trust_shift_delta": 0.0,
            "exposure_shift_delta": 0.0,
            "dependency_shift_delta": 0.0,
        }

        return {
            "project_id": str(project_id),
            "scene_id": str(scene_id),
            "episode_id": str(scene_context.get("episode_id")) if scene_context.get("episode_id") else None,
            "character_count": len(profiles),
            "intents": [intent.__dict__ for intent in intents],
            "tension": tension,
            "subtext_map": subtext_map,
            "power_shift": power_shift,
            "dominant_character_id": dominant_character_id,
            "drama_state": drama_state,
            "tension_breakdown": tension.get("breakdown", {}),
            "relationship_snapshot": graph_index,
            "relationship_shifts": power_shift.get("relationship_shifts", []),
            "status": "analyzed_stubbed",
        }


def graph_indexed_edges(graph_index: Dict[str, Dict[str, Any]]) -> List[Any]:
    edges: List[Any] = []
    for targets in graph_index.values():
        edges.extend(targets.values())
    return edges


def infer_dominant_character(graph_index: Dict[str, Dict[str, Any]]) -> Optional[str]:
    scores: Dict[str, float] = {}
    for source_id, targets in graph_index.items():
        scores.setdefault(source_id, 0.0)
        for snapshot in targets.values():
            scores[source_id] += float(getattr(snapshot, "dominance_source_over_target", 0.0) or 0.0)
    if not scores:
        return None
    return max(scores, key=scores.get)
