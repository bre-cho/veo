"""relationship_engine — updates and queries the relationship graph.

The relationship graph is a set of directed RelationshipEdge records.
This engine:
1. Applies scene outcome deltas to edges (``update_after_scene``).
2. Resolves the most relevant relationship for a character pair (``get_edge``).
3. Detects chemistry / tension between characters (``detect_chemistry``).
"""
from __future__ import annotations

from typing import Any


class RelationshipEngine:
    """Manages in-memory relationship graph mutations for a compile session."""

    def get_edge(
        self,
        source_id: str,
        target_id: str,
        relationships: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Return the relationship edge from source → target, or a neutral default."""
        for rel in relationships:
            if (
                rel.get("source_character_id") == source_id
                and rel.get("target_character_id") == target_id
            ):
                return rel
        return {
            "source_character_id": source_id,
            "target_character_id": target_id,
            "trust_level": 0.5,
            "fear_level": 0.0,
            "dominance_source_over_target": 0.5,
            "resentment_level": 0.0,
            "attraction_level": 0.0,
            "dependence_level": 0.0,
            "unresolved_tension_score": 0.0,
            "recent_betrayal_score": 0.0,
        }

    def detect_chemistry(
        self,
        source_id: str,
        target_id: str,
        relationships: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Compute chemistry score and dominant chemistry type for a pair.

        Returns
        -------
        dict with keys: chemistry_type, chemistry_score, tension_type
        """
        edge = self.get_edge(source_id, target_id, relationships)
        reverse = self.get_edge(target_id, source_id, relationships)

        attraction = (
            float(edge.get("attraction_level") or 0.0)
            + float(reverse.get("attraction_level") or 0.0)
        ) / 2
        rivalry = (
            float(edge.get("rivalry_level") or 0.0)
            + float(reverse.get("rivalry_level") or 0.0)
        ) / 2
        unresolved = (
            float(edge.get("unresolved_tension_score") or 0.0)
            + float(reverse.get("unresolved_tension_score") or 0.0)
        ) / 2
        betrayal = (
            float(edge.get("recent_betrayal_score") or 0.0)
            + float(reverse.get("recent_betrayal_score") or 0.0)
        ) / 2

        chemistry_score = round(
            attraction * 0.3 + rivalry * 0.25 + unresolved * 0.3 + betrayal * 0.15, 3
        )

        if betrayal > 0.4:
            chemistry_type = "betrayal_wound"
        elif attraction > 0.5 and unresolved > 0.4:
            chemistry_type = "forbidden_tension"
        elif rivalry > 0.5:
            chemistry_type = "power_clash"
        elif attraction > 0.5:
            chemistry_type = "mutual_pull"
        elif unresolved > 0.5:
            chemistry_type = "unfinished_business"
        else:
            chemistry_type = "neutral"

        tension_type = "suppressed" if chemistry_type in {
            "forbidden_tension", "unfinished_business"
        } else "explicit"

        return {
            "chemistry_type": chemistry_type,
            "chemistry_score": chemistry_score,
            "tension_type": tension_type,
        }

    def update_after_scene(
        self,
        edge: dict[str, Any],
        deltas: dict[str, float],
    ) -> dict[str, Any]:
        """Return an updated copy of the edge with deltas applied."""
        updated = dict(edge)
        for field, delta in deltas.items():
            if field in updated:
                updated[field] = round(max(0.0, min(1.0, float(updated[field]) + delta)), 3)
        return updated
