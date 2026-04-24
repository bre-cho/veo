from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class BlockingBeat:
    """A single blocking instruction anchored to a character and dramatic motive."""

    character_id: str
    action: str
    spatial_intent: str
    psychological_reason: str
    timing_hint: str = "mid-beat"


class BlockingEngine:
    """Maps power / exposure / relationship signals into staging instructions.

    This engine should remain deterministic and explainable. It is intended to be
    called after scene analysis and before render prompt compilation.
    """

    def build_plan(
        self,
        scene_context: Dict[str, Any],
        tension_breakdown: Dict[str, Any],
        power_shift: Dict[str, Any],
        relationship_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        participants: List[Dict[str, Any]] = scene_context.get("participants", [])
        dominant_character_id = power_shift.get("dominant_character_id") or scene_context.get(
            "dominant_character_id"
        )
        threatened_character_id = power_shift.get("threatened_character_id") or scene_context.get(
            "threatened_character_id"
        )
        emotional_center_id = scene_context.get("emotional_center_character_id")

        beats: List[BlockingBeat] = []
        for participant in participants:
            cid = str(participant.get("character_id") or participant.get("id") or "unknown")
            role = "neutral"
            action = "hold_position"
            spatial_intent = "maintain_scene_balance"
            reason = "Preserve readable geography while dramatic state remains unresolved."

            if cid == dominant_character_id:
                role = "dominant"
                action = "hold_center_then_pressure_space"
                spatial_intent = "control_axis"
                reason = "Character currently owns the scene's power and should visually control the frame."
            elif cid == threatened_character_id:
                role = "pressured"
                action = "shift_weight_back_or_guard_exit"
                spatial_intent = "protect_boundary"
                reason = "Character is under pressure and should visually defend space or escape routes."
            elif cid == emotional_center_id:
                role = "emotional_center"
                action = "stay_edge_visible_with_reaction_priority"
                spatial_intent = "anchor_internal_reaction"
                reason = "Character is the emotional lens of the scene and must remain readable."

            beats.append(
                BlockingBeat(
                    character_id=cid,
                    action=action,
                    spatial_intent=spatial_intent,
                    psychological_reason=reason,
                    timing_hint=self._timing_hint(role, tension_breakdown),
                )
            )

        return {
            "scene_id": scene_context.get("scene_id"),
            "dominant_character_id": dominant_character_id,
            "threatened_character_id": threatened_character_id,
            "emotional_center_character_id": emotional_center_id,
            "beats": [beat.__dict__ for beat in beats],
            "spatial_mode": self._spatial_mode(tension_breakdown, power_shift, relationship_snapshot),
            "blocking_notes": self._build_notes(tension_breakdown, power_shift),
        }

    def _timing_hint(self, role: str, tension_breakdown: Dict[str, Any]) -> str:
        tension_score = float(tension_breakdown.get("tension_score", 0.0))
        if role == "dominant":
            return "early-beat" if tension_score < 60 else "turning-point"
        if role == "pressured":
            return "pre-turn" if tension_score < 60 else "late-beat"
        if role == "emotional_center":
            return "reaction-hold"
        return "mid-beat"

    def _spatial_mode(
        self,
        tension_breakdown: Dict[str, Any],
        power_shift: Dict[str, Any],
        relationship_snapshot: Optional[Dict[str, Any]],
    ) -> str:
        tension_score = float(tension_breakdown.get("tension_score", 0.0))
        if power_shift.get("outcome_type") in {"moral_power_flip", "dominance_flip"}:
            return "recenter_after_flip"
        if relationship_snapshot and relationship_snapshot.get("betrayal_risk", 0) > 0.7:
            return "triangular_distance"
        if tension_score >= 75:
            return "compressed_space"
        return "stable_geometry"

    def _build_notes(self, tension_breakdown: Dict[str, Any], power_shift: Dict[str, Any]) -> List[str]:
        notes: List[str] = []
        if float(tension_breakdown.get("exposure_risk", 0.0)) > 0.65:
            notes.append("Keep vulnerable characters readable; do not hide the exposure moment with decorative movement.")
        if power_shift.get("dominant_character_id") != power_shift.get("previous_dominant_character_id"):
            notes.append("Update stage geography after the turn so spatial control matches the new power holder.")
        if not notes:
            notes.append("Preserve clean eye-lines and let blocking serve the psychological hierarchy.")
        return notes
