from __future__ import annotations

from typing import Any, Dict, List, Optional


class SubtextEngine:
    """Generates structured subtext suggestions for dialogue beats.

    This is intentionally rule-based for phase 2. It should eventually be replaced or
    augmented by a model-backed planner.
    """

    def infer_dialogue_actions(
        self,
        speaker_profile: Any,
        target_profile: Any,
        relationship_forward: Optional[Any],
        scene_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        scene_context = scene_context or {}

        act = "probe"
        hidden_intent = "Test the other character's position"

        trust = float(getattr(relationship_forward, "trust_level", 0.0) or 0.0) if relationship_forward else 0.0
        resentment = float(getattr(relationship_forward, "resentment_level", 0.0) or 0.0) if relationship_forward else 0.0
        dominance = float(getattr(relationship_forward, "dominance_source_over_target", 0.0) or 0.0) if relationship_forward else 0.0

        if resentment > 0.6:
            act = "attack"
            hidden_intent = "Punish while maintaining plausible deniability"
        elif dominance > 0.6:
            act = "dominate"
            hidden_intent = "Narrow the other character's perceived options"
        elif trust > 0.6:
            act = "reassure"
            hidden_intent = "Stabilize alliance and preserve emotional access"
        elif getattr(speaker_profile, "archetype", None) == "Manipulator":
            act = "redirect"
            hidden_intent = "Change frame before accountability lands"

        return {
            "speaker_id": str(speaker_profile.id),
            "target_id": str(target_profile.id),
            "psychological_action": act,
            "hidden_intent": hidden_intent,
            "suggested_subtext": getattr(speaker_profile, "mask_strategy", None)
            or "Conceal true stakes behind cleaner language",
            "threat_level": scene_context.get("exposure_risk", 0.3),
        }
