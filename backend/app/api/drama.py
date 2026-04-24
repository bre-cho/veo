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

POST /api/v1/drama/compile/render-bridge
    Compile a scene and return the full render-bridge payload (item 25).

POST /api/v1/drama/compile/acting-bridge
    Compile a scene and return per-character Avatar Acting Model inputs (item 21).

POST /api/v1/drama/validate/fake-drama
    Validate a compiled drama result against the 5 anti-fake-drama rules (item 23).

POST /api/v1/drama/telemetry/scene
    Compute scene-level telemetry / scorecard (item 22).

POST /api/v1/drama/telemetry/episode
    Aggregate episode-level telemetry from multiple scene results (item 22).

POST /api/v1/drama/tournament/run
    Run a scene variant tournament (item 26).

GET  /api/v1/drama/tournament/dna
    Return all stored winner DNA entries (item 26).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.schemas.drama import DramaCompileRequest
from app.services.drama.drama_compiler_service import DramaCompilerService
from app.services.drama.character_intent_engine import CharacterIntentEngine
from app.services.drama.tension_engine import TensionEngine
from app.services.drama.drama_acting_bridge import DramaActingBridge
from app.services.drama.fake_drama_validator import FakeDramaValidator
from app.services.drama.drama_telemetry_engine import DramaTelemetryEngine
from app.services.drama.render_bridge_service import RenderBridgeService
from app.services.drama.scene_tournament_engine import (
    SceneTournamentEngine,
    list_winner_dna,
)

router = APIRouter(tags=["drama"])

_compiler = DramaCompilerService()
_intent_engine = CharacterIntentEngine()
_tension_engine = TensionEngine()
_acting_bridge = DramaActingBridge()
_fake_validator = FakeDramaValidator()
_telemetry_engine = DramaTelemetryEngine()
_render_bridge = RenderBridgeService()
_tournament_engine = SceneTournamentEngine()


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


class RenderBridgeRequest(BaseModel):
    """Request for the render-bridge compile endpoint."""

    project_id: str
    scene_id: str
    episode_id: str | None = None
    beat: dict[str, Any]
    characters: list[dict[str, Any]]
    character_states: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    memory_traces: list[dict[str, Any]] = Field(default_factory=list)
    arc_progresses: list[dict[str, Any]] = Field(default_factory=list)
    scene_history: list[dict[str, Any]] = Field(default_factory=list)
    previous_states: dict[str, dict[str, Any]] = Field(default_factory=dict)


class FakeDramaValidateRequest(BaseModel):
    """Request for fake-drama validation."""

    drama_result: dict[str, Any]
    scene_history: list[dict[str, Any]] = Field(default_factory=list)
    previous_states: dict[str, dict[str, Any]] = Field(default_factory=dict)
    characters: list[dict[str, Any]] = Field(default_factory=list)


class SceneTelemetryRequest(BaseModel):
    """Request for scene-level telemetry computation."""

    scene_id: str
    project_id: str
    episode_id: str | None = None
    drama_result: dict[str, Any]
    fake_drama_violations: list[str] = Field(default_factory=list)


class EpisodeTelemetryRequest(BaseModel):
    """Request for episode-level telemetry aggregation."""

    project_id: str
    episode_id: str
    scene_telemetry_list: list[dict[str, Any]]
    drama_results: list[dict[str, Any]]


class TournamentRequest(BaseModel):
    """Request for the scene tournament engine."""

    project_id: str
    scene_id: str
    episode_id: str | None = None
    base_beat: dict[str, Any]
    characters: list[dict[str, Any]]
    character_states: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    memory_traces: list[dict[str, Any]] = Field(default_factory=list)
    arc_progresses: list[dict[str, Any]] = Field(default_factory=list)
    num_variants: int = 3


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


# ---------------------------------------------------------------------------
# Item 21: Drama → Avatar Acting Model bridge
# ---------------------------------------------------------------------------

@router.post("/api/v1/drama/compile/acting-bridge")
def compile_drama_acting_bridge(payload: RenderBridgeRequest) -> dict[str, Any]:
    """Compile a scene and return per-character Avatar Acting Model inputs.

    The Drama Engine provides causal context (why characters act as they do)
    and the Avatar Acting Model uses it for physical expression decisions.
    """
    drama_result = _compiler.compile(
        project_id=payload.project_id,
        scene_id=payload.scene_id,
        episode_id=payload.episode_id,
        beat=payload.beat,
        characters=payload.characters,
        character_states=payload.character_states,
        relationships=payload.relationships,
        memory_traces=payload.memory_traces,
        arc_progresses=payload.arc_progresses,
    )
    acting_inputs = _acting_bridge.build_acting_inputs(drama_result)
    return {
        "ok": True,
        "scene_id": payload.scene_id,
        "acting_inputs": acting_inputs,
        "drama_summary": {
            "outcome_type": drama_result.get("scene_drama", {}).get("outcome_type"),
            "dominant_character_id": drama_result.get("scene_drama", {}).get("dominant_character_id"),
            "scene_temperature": drama_result.get("tension_analysis", {}).get("scene_temperature"),
        },
    }


# ---------------------------------------------------------------------------
# Item 22: Telemetry / Scorecard
# ---------------------------------------------------------------------------

@router.post("/api/v1/drama/telemetry/scene")
def compute_scene_telemetry(payload: SceneTelemetryRequest) -> dict[str, Any]:
    """Compute scene-level telemetry / scorecard from a compiled drama result."""
    result = _telemetry_engine.compute_scene_telemetry(
        scene_id=payload.scene_id,
        project_id=payload.project_id,
        episode_id=payload.episode_id,
        drama_result=payload.drama_result,
        fake_drama_violations=payload.fake_drama_violations,
    )
    char_telemetry = _telemetry_engine.compute_character_telemetry(
        scene_id=payload.scene_id,
        project_id=payload.project_id,
        drama_result=payload.drama_result,
    )
    return {"ok": True, "scene": result, "characters": char_telemetry}


@router.post("/api/v1/drama/telemetry/episode")
def compute_episode_telemetry(payload: EpisodeTelemetryRequest) -> dict[str, Any]:
    """Aggregate episode-level telemetry from multiple scene compilations."""
    result = _telemetry_engine.compute_episode_telemetry(
        project_id=payload.project_id,
        episode_id=payload.episode_id,
        scene_telemetry_list=payload.scene_telemetry_list,
        drama_results=payload.drama_results,
    )
    return {"ok": True, "episode": result}


# ---------------------------------------------------------------------------
# Item 23: Anti-fake-drama validation
# ---------------------------------------------------------------------------

@router.post("/api/v1/drama/validate/fake-drama")
def validate_fake_drama(payload: FakeDramaValidateRequest) -> dict[str, Any]:
    """Validate a compiled drama result against the 5 anti-fake-drama rules."""
    violations = _fake_validator.validate(
        drama_result=payload.drama_result,
        scene_history=payload.scene_history or None,
        previous_states=payload.previous_states or None,
        characters=payload.characters or None,
    )
    return {
        "ok": True,
        "violations": violations,
        "violation_count": len(violations),
        "passed": len(violations) == 0,
    }


# ---------------------------------------------------------------------------
# Item 25: Render bridge output
# ---------------------------------------------------------------------------

@router.post("/api/v1/drama/compile/render-bridge")
def compile_render_bridge(payload: RenderBridgeRequest) -> dict[str, Any]:
    """Compile a scene and return the full render-bridge payload.

    Combines Drama Engine output, telemetry, fake-drama validation and camera
    planning into the format consumed by the render pipeline.
    """
    drama_result = _compiler.compile(
        project_id=payload.project_id,
        scene_id=payload.scene_id,
        episode_id=payload.episode_id,
        beat=payload.beat,
        characters=payload.characters,
        character_states=payload.character_states,
        relationships=payload.relationships,
        memory_traces=payload.memory_traces,
        arc_progresses=payload.arc_progresses,
    )
    bridge_payload = _render_bridge.build(
        scene_id=payload.scene_id,
        project_id=payload.project_id,
        episode_id=payload.episode_id,
        drama_result=drama_result,
        scene_history=payload.scene_history or None,
        previous_states=payload.previous_states or None,
    )
    return {"ok": True, **bridge_payload}


# ---------------------------------------------------------------------------
# Item 26: Scene Tournament Engine
# ---------------------------------------------------------------------------

@router.post("/api/v1/drama/tournament/run")
def run_scene_tournament(payload: TournamentRequest) -> dict[str, Any]:
    """Generate 2–4 scene variants, score them, return the winner and store DNA."""
    result = _tournament_engine.run_tournament(
        project_id=payload.project_id,
        scene_id=payload.scene_id,
        episode_id=payload.episode_id,
        base_beat=payload.base_beat,
        characters=payload.characters,
        character_states=payload.character_states or None,
        relationships=payload.relationships or None,
        memory_traces=payload.memory_traces or None,
        arc_progresses=payload.arc_progresses or None,
        num_variants=payload.num_variants,
    )
    return {"ok": True, **result}


@router.get("/api/v1/drama/tournament/dna")
def get_tournament_dna() -> dict[str, Any]:
    """Return all stored winner DNA entries for relationship archetypes."""
    return {"ok": True, "dna_store": list_winner_dna()}
