"""avatar_relationship_engine — manages dynamic avatar ↔ entity relationship state.

Relationship levels shift after scene outcomes (betrayal, reconciliation, etc.)
and are used by the motivation engine to calibrate power dynamics.
"""
from __future__ import annotations

from typing import Any

# Relationship shifts triggered by scene outcomes
_OUTCOME_SHIFTS: dict[str, dict[str, float]] = {
    "betrayal": {"trust_level": -0.3, "resentment_level": +0.3},
    "reconciliation": {"trust_level": +0.2, "resentment_level": -0.1},
    "victory_over": {"dominance_level": +0.2, "fear_level": -0.1},
    "defeat_by": {"dominance_level": -0.2, "fear_level": +0.15},
    "dependency_increased": {"dependency_level": +0.2},
    "attraction_event": {"attraction_level": +0.15},
    "threat_received": {"fear_level": +0.2, "trust_level": -0.1},
}


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


class AvatarRelationshipEngine:
    """Updates and retrieves relationship state between an avatar and other entities."""

    def get_state(
        self,
        db: Any | None,
        *,
        avatar_id: str,
        target_entity_id: str,
    ) -> dict[str, Any]:
        """Retrieve current relationship state from DB or return defaults."""
        if db is not None:
            try:
                from app.models.avatar_relationship_state import AvatarRelationshipState

                row = (
                    db.query(AvatarRelationshipState)
                    .filter(
                        AvatarRelationshipState.avatar_id == avatar_id,
                        AvatarRelationshipState.target_entity_id == target_entity_id,
                    )
                    .first()
                )
                if row is not None:
                    return {
                        "avatar_id": row.avatar_id,
                        "target_entity_id": row.target_entity_id,
                        "trust_level": row.trust_level,
                        "fear_level": row.fear_level,
                        "dominance_level": row.dominance_level,
                        "resentment_level": row.resentment_level,
                        "attraction_level": row.attraction_level,
                        "dependency_level": row.dependency_level,
                    }
            except Exception:
                pass

        # Default neutral relationship
        return {
            "avatar_id": avatar_id,
            "target_entity_id": target_entity_id,
            "trust_level": 0.5,
            "fear_level": 0.0,
            "dominance_level": 0.5,
            "resentment_level": 0.0,
            "attraction_level": 0.0,
            "dependency_level": 0.0,
        }

    def update_from_outcome(
        self,
        db: Any | None,
        *,
        avatar_id: str,
        target_entity_id: str,
        scene_outcome: str,
    ) -> dict[str, Any]:
        """Apply relationship shifts based on *scene_outcome* and persist.

        Returns the updated state dict.
        """
        state = self.get_state(db, avatar_id=avatar_id, target_entity_id=target_entity_id)
        shifts = _OUTCOME_SHIFTS.get(scene_outcome, {})

        for key, delta in shifts.items():
            state[key] = _clamp(float(state.get(key, 0.5)) + delta)

        if db is not None:
            try:
                from app.models.avatar_relationship_state import AvatarRelationshipState

                row = (
                    db.query(AvatarRelationshipState)
                    .filter(
                        AvatarRelationshipState.avatar_id == avatar_id,
                        AvatarRelationshipState.target_entity_id == target_entity_id,
                    )
                    .first()
                )
                if row is None:
                    row = AvatarRelationshipState(
                        avatar_id=avatar_id,
                        target_entity_id=target_entity_id,
                    )
                    db.add(row)

                row.trust_level = state["trust_level"]
                row.fear_level = state["fear_level"]
                row.dominance_level = state["dominance_level"]
                row.resentment_level = state["resentment_level"]
                row.attraction_level = state["attraction_level"]
                row.dependency_level = state["dependency_level"]
                db.commit()
            except Exception:
                pass

        return state
