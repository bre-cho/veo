from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class CharacterIntentResult:
    character_id: str
    outer_goal: Optional[str]
    hidden_need: Optional[str]
    fear_trigger: Optional[str]
    mask_strategy: Optional[str]
    likely_scene_intent: str
    pressure_response: Optional[str]
    notes: List[str]


class CharacterIntentEngine:
    """Derives per-character scene intent from profile + optional beat context.

    The goal here is not to generate prose, but to give downstream engines a compact,
    machine-readable intent package.
    """

    def derive(self, profile: Any, scene_context: Optional[Dict[str, Any]] = None) -> CharacterIntentResult:
        scene_context = scene_context or {}
        beat_goal = scene_context.get("scene_goal")

        if beat_goal and getattr(profile, "outer_goal", None):
            likely_scene_intent = f"Pursue outer goal through scene goal: {beat_goal}"
        elif getattr(profile, "outer_goal", None):
            likely_scene_intent = f"Advance outer goal: {profile.outer_goal}"
        else:
            likely_scene_intent = "Probe scene and protect self-position"

        notes: List[str] = []
        if getattr(profile, "dominant_fear", None):
            notes.append(f"Avoid trigger: {profile.dominant_fear}")
        if getattr(profile, "public_persona", None) and getattr(profile, "private_self", None):
            notes.append("Mask tension present between public persona and private self")

        return CharacterIntentResult(
            character_id=str(profile.id),
            outer_goal=getattr(profile, "outer_goal", None),
            hidden_need=getattr(profile, "hidden_need", None),
            fear_trigger=getattr(profile, "dominant_fear", None),
            mask_strategy=getattr(profile, "mask_strategy", None),
            likely_scene_intent=likely_scene_intent,
            pressure_response=getattr(profile, "pressure_response", None),
            notes=notes,
        )
