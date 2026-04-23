"""drama — REST API for the Multi-Character Drama Engine.

Endpoints
---------
POST /api/v1/drama/compile
    Full drama compilation for a scene beat.  Takes a DramaCompileRequest
    and returns a DramaCompileResponse.

POST /api/v1/drama/characters/intent
    Resolve scene goal and hidden intent for a single character.

POST /api/v1/drama/tension
    Compute scene tension from character states and relationships.

GET  /api/v1/drama/archetype-presets
    Return all archetype preset seed definitions.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.schemas.drama import DramaCompileRequest
from app.services.drama.drama_compiler_service import DramaCompilerService
from app.services.drama.character_intent_engine import CharacterIntentEngine
from app.services.drama.tension_engine import TensionEngine

router = APIRouter(tags=["drama"])

_compiler = DramaCompilerService()
_intent_engine = CharacterIntentEngine()
_tension_engine = TensionEngine()


# ---------------------------------------------------------------------------
# Archetype presets (drama-aware)
# ---------------------------------------------------------------------------

DRAMA_ARCHETYPE_PRESETS: dict[str, dict[str, Any]] = {
    "mentor": {
        "speech_tempo": "slow",
        "pause_style": "long",
        "gaze_style": "stable",
        "movement": "minimal",
        "pressure_response": "deepen_calm",
        "dominance_style": "quiet_control",
        "defense_style": "absorb_then_reframe",
        "likely_subtext": "i_already_know_more_than_i_say",
    },
    "manipulator": {
        "speech_tempo": "variable",
        "pause_style": "calculated",
        "gaze_style": "avoid_then_lock",
        "movement": "relaxed_control",
        "pressure_response": "deflect_seduce_reframe",
        "dominance_style": "psychological_control",
        "defense_style": "charm_blame_frame_shift",
        "likely_subtext": "i_control_the_meaning_of_this_moment",
    },
    "rebel": {
        "speech_tempo": "fast",
        "pause_style": "short",
        "gaze_style": "direct_confrontational",
        "movement": "body_leads_words",
        "pressure_response": "explode_or_exit",
        "dominance_style": "force_presence",
        "defense_style": "confrontation_or_withdrawal",
        "likely_subtext": "you_will_not_control_me",
    },
    "wounded_observer": {
        "speech_tempo": "slow",
        "pause_style": "frequent",
        "gaze_style": "avoid_sustained_contact",
        "movement": "contracted_minimal",
        "pressure_response": "silence_swallow_feeling",
        "dominance_style": "hidden_reading",
        "defense_style": "retreat_inward",
        "likely_subtext": "i_see_everything_but_cannot_safely_say_it",
    },
    "authority": {
        "speech_tempo": "deliberate",
        "pause_style": "strategic",
        "gaze_style": "top_down",
        "movement": "economical",
        "pressure_response": "look_down_slow_tighten",
        "dominance_style": "structural_control",
        "defense_style": "silent_intimidation",
        "likely_subtext": "you_exist_inside_my_frame",
    },
}


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class CharacterIntentRequest(BaseModel):
    character_profile: dict[str, Any]
    beat: dict[str, Any]
    character_state: dict[str, Any] | None = None
    relationship_state: dict[str, Any] | None = None


class TensionRequest(BaseModel):
    beat: dict[str, Any]
    character_states: list[dict[str, Any]]
    relationships: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/api/v1/drama/compile")
def compile_drama(payload: DramaCompileRequest) -> dict[str, Any]:
    """Run full Multi-Character Drama Engine for a scene beat."""
    result = _compiler.compile(
        project_id=payload.project_id,
        scene_id=payload.scene_id,
        episode_id=payload.episode_id,
        beat=payload.beat,
        characters=[c.model_dump() for c in payload.characters],
        character_states=[s.model_dump() for s in payload.character_states],
        relationships=[r.model_dump() for r in payload.relationships],
        memory_traces=payload.memory_traces,
    )
    return result


@router.post("/api/v1/drama/characters/intent")
def resolve_character_intent(payload: CharacterIntentRequest) -> dict[str, Any]:
    """Resolve scene goal and hidden intent for a single character."""
    result = _intent_engine.resolve(
        character_profile=payload.character_profile,
        beat=payload.beat,
        character_state=payload.character_state,
        relationship_state=payload.relationship_state,
    )
    return {"ok": True, "data": result}


@router.post("/api/v1/drama/tension")
def compute_tension(payload: TensionRequest) -> dict[str, Any]:
    """Compute scene tension from character states and relationships."""
    result = _tension_engine.compute(
        beat=payload.beat,
        character_states=payload.character_states,
        relationships=payload.relationships,
    )
    return {"ok": True, "data": result}


@router.get("/api/v1/drama/archetype-presets")
def get_drama_archetype_presets() -> dict[str, Any]:
    """Return all built-in drama archetype presets."""
    return {"ok": True, "data": DRAMA_ARCHETYPE_PRESETS}
