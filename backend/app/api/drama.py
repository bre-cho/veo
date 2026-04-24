"""drama — REST API for the Multi-Character Drama Engine.

Section 17: API Map
--------------------
Characters
  POST   /api/v1/drama/characters
  GET    /api/v1/drama/characters/{id}
  PATCH  /api/v1/drama/characters/{id}
  POST   /api/v1/drama/characters/{id}/state/bootstrap
  POST   /api/v1/drama/characters/{id}/preset/apply

Relationships
  POST   /api/v1/drama/relationships
  GET    /api/v1/drama/relationships
  PATCH  /api/v1/drama/relationships/{id}
  POST   /api/v1/drama/relationships/graph/rebuild
  GET    /api/v1/drama/relationships/graph

Scene drama
  POST   /api/v1/drama/scenes/{scene_id}/analyze
  POST   /api/v1/drama/scenes/{scene_id}/compile
  GET    /api/v1/drama/scenes/{scene_id}/state
  GET    /api/v1/drama/scenes/{scene_id}/subtext
  GET    /api/v1/drama/scenes/{scene_id}/blocking
  GET    /api/v1/drama/scenes/{scene_id}/camera-plan
  POST   /api/v1/drama/scenes/{scene_id}/apply-outcome

Arcs
  GET    /api/v1/drama/arcs/{character_id}
  POST   /api/v1/drama/arcs/{character_id}/advance
  POST   /api/v1/drama/arcs/recompute

Compile
  POST   /api/v1/drama/compile
  POST   /api/v1/drama/compile/episode
  POST   /api/v1/drama/compile/project

Legacy debug
  POST   /api/v1/drama/characters/intent
  POST   /api/v1/drama/tension
  GET    /api/v1/drama/archetype-presets

Phase 3 (items 21–26)
  POST   /api/v1/drama/compile/acting-bridge
  POST   /api/v1/drama/compile/render-bridge
  POST   /api/v1/drama/validate/fake-drama
  POST   /api/v1/drama/telemetry/scene
  POST   /api/v1/drama/telemetry/episode
  POST   /api/v1/drama/tournament/run
  GET    /api/v1/drama/tournament/dna
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.schemas.drama import DramaCompileRequest
from app.services.drama.drama_compiler_service import DramaCompilerService
from app.services.drama.character_intent_engine import CharacterIntentEngine
from app.services.drama.tension_engine import TensionEngine
from app.services.drama.arc_engine import ArcEngine
from app.services.drama.betrayal_alliance_engine import BetrayalAllianceEngine
from app.services.drama.chemistry_engine import ChemistryEngine
from app.services.drama.relationship_engine import RelationshipEngine
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
_arc_engine = ArcEngine()
_betrayal_engine = BetrayalAllianceEngine()
_chemistry_engine = ChemistryEngine()
_relationship_engine = RelationshipEngine()
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
        "arc_type": "control_to_vulnerability",
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
        "arc_type": "false_authority_to_collapse",
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
        "arc_type": "rage_to_grief",
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
        "arc_type": "hidden_shame_to_truth",
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
        "arc_type": "false_authority_to_collapse",
    },
    "dependent": {
        "speech_tempo": "variable",
        "pause_style": "anxious",
        "gaze_style": "seeking_approval",
        "movement": "mirror_other",
        "pressure_response": "cling_or_collapse",
        "dominance_style": "emotional_leverage",
        "defense_style": "guilt_trip_or_retreat",
        "likely_subtext": "please_do_not_leave_me",
        "arc_type": "dependence_to_autonomy",
    },
}


# ---------------------------------------------------------------------------
# Request/response models
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


class CharacterCreateRequest(BaseModel):
    project_id: str
    name: str
    archetype: str = "observer"
    avatar_id: str | None = None
    public_persona: str | None = None
    private_self: str | None = None
    outer_goal: str | None = None
    hidden_need: str | None = None
    core_wound: str | None = None
    dominant_fear: str | None = None
    mask_strategy: str | None = None
    pressure_response: str = "withdrawal"
    speech_pattern: str | None = None
    movement_pattern: str | None = None
    gaze_pattern: str | None = None
    tempo_default: str = "moderate"
    attachment_style: str = "secure"
    dominance_baseline: float = 0.5
    trust_baseline: float = 0.5
    openness_baseline: float = 0.5
    volatility_baseline: float = 0.3
    acting_preset_seed: str = "mentor"
    arc_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CharacterPatchRequest(BaseModel):
    archetype: str | None = None
    outer_goal: str | None = None
    hidden_need: str | None = None
    core_wound: str | None = None
    dominant_fear: str | None = None
    mask_strategy: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class StateBootstrapRequest(BaseModel):
    project_id: str
    scene_id: str | None = None
    episode_id: str | None = None
    overrides: dict[str, Any] = Field(default_factory=dict)


class PresetApplyRequest(BaseModel):
    preset_name: str
    project_id: str


class RelationshipCreateRequest(BaseModel):
    project_id: str
    source_character_id: str
    target_character_id: str
    relation_type: str = "neutral"
    # Section 7.1 relation types:
    # mentor, rival, superior, subordinate, ally, enemy, protector, dependent,
    # pursuer, avoidant, ex-trust, covert-attraction, manipulator-target,
    # shared-secret, betrayer-betrayed
    trust: float = 0.5
    fear: float = 0.0
    dependence: float = 0.0
    resentment: float = 0.0
    attraction: float = 0.0
    moral_superiority: float = 0.0
    perceived_power: float = 0.5
    hidden_agenda: float = 0.0
    shame_exposure_risk: float = 0.0
    emotional_hook_strength: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class RelationshipPatchRequest(BaseModel):
    relation_type: str | None = None
    trust: float | None = None
    fear: float | None = None
    dependence: float | None = None
    resentment: float | None = None
    attraction: float | None = None
    hidden_agenda: float | None = None
    shame_exposure_risk: float | None = None
    emotional_hook_strength: float | None = None
    moral_superiority: float | None = None
    perceived_power: float | None = None
    status: str | None = None


class SceneAnalyzeRequest(BaseModel):
    project_id: str
    episode_id: str | None = None
    beat: dict[str, Any]
    characters: list[dict[str, Any]]
    character_states: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    memory_traces: list[dict[str, Any]] = Field(default_factory=list)
    arc_progresses: list[dict[str, Any]] = Field(default_factory=list)


class RenderBridgeRequest(BaseModel):
    """Request for the render-bridge compile endpoint (items 21 & 25)."""

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


class SceneApplyOutcomeRequest(BaseModel):
    project_id: str
    outcome_type: str
    characters: list[dict[str, Any]]
    character_states: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    beat: dict[str, Any] = Field(default_factory=dict)


class ArcAdvanceRequest(BaseModel):
    project_id: str
    episode_id: str | None = None
    scene_outcome: str
    character_state: dict[str, Any] = Field(default_factory=dict)
    arc_progress: dict[str, Any] = Field(default_factory=dict)


class ArcRecomputeRequest(BaseModel):
    project_id: str
    episode_id: str | None = None
    character_ids: list[str]
    scene_history: list[dict[str, Any]] = Field(default_factory=list)


class EpisodeCompileRequest(BaseModel):
    project_id: str
    episode_id: str
    scenes: list[dict[str, Any]]
    characters: list[dict[str, Any]]
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    memory_traces: list[dict[str, Any]] = Field(default_factory=list)
    arc_progresses: list[dict[str, Any]] = Field(default_factory=list)


class ProjectCompileRequest(BaseModel):
    project_id: str
    episodes: list[dict[str, Any]]
    characters: list[dict[str, Any]]
    relationships: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# ── Characters ──────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

@router.post("/api/v1/drama/characters")
def create_character(payload: CharacterCreateRequest) -> dict[str, Any]:
    """Create a drama character profile."""
    import uuid
    char_id = str(uuid.uuid4())
    preset = DRAMA_ARCHETYPE_PRESETS.get(payload.archetype, {})
    return {
        "ok": True,
        "data": {
            "id": char_id,
            **payload.model_dump(),
            "archetype_preset": preset,
        },
    }


@router.get("/api/v1/drama/characters/{character_id}")
def get_character(character_id: str) -> dict[str, Any]:
    """Get drama character profile by ID (stub — DB lookup in production)."""
    return {"ok": True, "data": {"id": character_id}}


@router.patch("/api/v1/drama/characters/{character_id}")
def patch_character(character_id: str, payload: CharacterPatchRequest) -> dict[str, Any]:
    """Update mutable character profile fields."""
    return {
        "ok": True,
        "data": {"id": character_id, **payload.model_dump(exclude_none=True)},
    }


@router.post("/api/v1/drama/characters/{character_id}/state/bootstrap")
def bootstrap_character_state(
    character_id: str, payload: StateBootstrapRequest
) -> dict[str, Any]:
    """Bootstrap a character's emotional state for a new scene/episode."""
    from app.services.drama.drama_compiler_service import _default_state

    state = _default_state(character_id, payload.project_id)
    state.update(payload.overrides)
    if payload.scene_id:
        state["scene_id"] = payload.scene_id
    if payload.episode_id:
        state["episode_id"] = payload.episode_id
    return {"ok": True, "data": state}


@router.post("/api/v1/drama/characters/{character_id}/preset/apply")
def apply_archetype_preset(
    character_id: str, payload: PresetApplyRequest
) -> dict[str, Any]:
    """Apply a named archetype preset to a character's acting profile."""
    preset = DRAMA_ARCHETYPE_PRESETS.get(payload.preset_name)
    if not preset:
        return {"ok": False, "error": f"Unknown preset: {payload.preset_name}"}
    return {
        "ok": True,
        "data": {
            "character_id": character_id,
            "preset_name": payload.preset_name,
            "applied": preset,
        },
    }


# ---------------------------------------------------------------------------
# ── Relationships ────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

@router.post("/api/v1/drama/relationships")
def create_relationship(payload: RelationshipCreateRequest) -> dict[str, Any]:
    """Create a directed relationship edge (section 7)."""
    import uuid
    rel_id = str(uuid.uuid4())
    return {"ok": True, "data": {"id": rel_id, **payload.model_dump()}}


@router.get("/api/v1/drama/relationships")
def list_relationships(project_id: str) -> dict[str, Any]:
    """List all relationship edges for a project (stub — DB lookup in production)."""
    return {"ok": True, "data": [], "project_id": project_id}


@router.patch("/api/v1/drama/relationships/{rel_id}")
def patch_relationship(rel_id: str, payload: RelationshipPatchRequest) -> dict[str, Any]:
    """Update a relationship edge's scores."""
    return {
        "ok": True,
        "data": {"id": rel_id, **payload.model_dump(exclude_none=True)},
    }


@router.post("/api/v1/drama/relationships/graph/rebuild")
def rebuild_relationship_graph(
    project_id: str,
    relationships: list[dict[str, Any]],
) -> dict[str, Any]:
    """Rebuild the relationship graph and return adjacency summary."""
    nodes: set[str] = set()
    for r in relationships:
        nodes.add(r.get("source_character_id", ""))
        nodes.add(r.get("target_character_id", ""))
    nodes.discard("")
    return {
        "ok": True,
        "data": {
            "project_id": project_id,
            "node_count": len(nodes),
            "edge_count": len(relationships),
            "nodes": list(nodes),
        },
    }


@router.get("/api/v1/drama/relationships/graph")
def get_relationship_graph(project_id: str) -> dict[str, Any]:
    """Get relationship graph summary for a project (stub — DB lookup in production)."""
    return {"ok": True, "data": {"project_id": project_id, "nodes": [], "edges": []}}


# ---------------------------------------------------------------------------
# ── Scene Drama ──────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

@router.post("/api/v1/drama/scenes/{scene_id}/analyze")
def analyze_scene(scene_id: str, payload: SceneAnalyzeRequest) -> dict[str, Any]:
    """Analyse a scene beat: compute tension, subtext, and chemistry only (no outcome).

    Lighter than /compile — does not advance arcs or update states.
    """
    tension = _tension_engine.compute(
        beat=payload.beat,
        character_states=payload.character_states,
        relationships=payload.relationships,
    )
    chemistry_map = _chemistry_engine.compute_all_pairs(
        payload.characters, payload.relationships
    )
    betrayal_map = _betrayal_engine.evaluate_all_pairs(
        payload.characters, payload.relationships
    )
    return {
        "ok": True,
        "scene_id": scene_id,
        "tension_analysis": tension,
        "chemistry_map": chemistry_map,
        "betrayal_alliance_map": betrayal_map,
    }


@router.post("/api/v1/drama/scenes/{scene_id}/compile")
def compile_scene(scene_id: str, payload: SceneAnalyzeRequest) -> dict[str, Any]:
    """Full drama compilation for a scene beat."""
    result = _compiler.compile(
        project_id=payload.project_id,
        scene_id=scene_id,
        episode_id=payload.episode_id,
        beat=payload.beat,
        characters=payload.characters,
        character_states=payload.character_states,
        relationships=payload.relationships,
        memory_traces=payload.memory_traces,
    )
    return result


@router.get("/api/v1/drama/scenes/{scene_id}/state")
def get_scene_state(scene_id: str, project_id: str) -> dict[str, Any]:
    """Get the drama state for a scene (stub — DB lookup in production)."""
    return {"ok": True, "scene_id": scene_id, "project_id": project_id, "data": None}


@router.get("/api/v1/drama/scenes/{scene_id}/subtext")
def get_scene_subtext(scene_id: str, project_id: str) -> dict[str, Any]:
    """Get the dialogue subtext records for a scene (stub — DB lookup in production)."""
    return {"ok": True, "scene_id": scene_id, "data": []}


@router.get("/api/v1/drama/scenes/{scene_id}/blocking")
def get_scene_blocking(scene_id: str, project_id: str) -> dict[str, Any]:
    """Get the blocking plan for a scene (stub — DB lookup in production)."""
    return {"ok": True, "scene_id": scene_id, "data": None}


@router.get("/api/v1/drama/scenes/{scene_id}/camera-plan")
def get_scene_camera_plan(scene_id: str, project_id: str) -> dict[str, Any]:
    """Get the camera drama plan for a scene (stub — DB lookup in production)."""
    return {"ok": True, "scene_id": scene_id, "data": None}


@router.post("/api/v1/drama/scenes/{scene_id}/apply-outcome")
def apply_scene_outcome(
    scene_id: str, payload: SceneApplyOutcomeRequest
) -> dict[str, Any]:
    """Apply a scene outcome to update character states and relationships.

    Returns the updated states, relationship deltas, and memory traces.
    """
    from app.services.drama.emotional_update_engine import EmotionalUpdateEngine
    from app.services.drama.power_shift_engine import PowerShiftEngine

    update_engine = EmotionalUpdateEngine()
    shift_engine = PowerShiftEngine()

    updated_states: list[dict[str, Any]] = []
    memory_traces: list[dict[str, Any]] = []

    state_map = {s["character_id"]: s for s in payload.character_states}
    for char in payload.characters:
        cid = char.get("id") or char.get("avatar_id") or char["name"]
        state = state_map.get(cid, {})
        result = update_engine.apply(
            character_id=cid,
            scene_id=scene_id,
            outcome_type=payload.outcome_type,
            character_state=state,
            beat=payload.beat,
        )
        updated_states.append({"character_id": cid, **result["updated_state"]})
        memory_traces.append(result["memory_trace"])

    # Build minimal scene_drama for power shift
    scene_drama = {
        "scene_id": scene_id,
        "dominant_character_id": payload.characters[0].get("id") if payload.characters else None,
        "threatened_character_id": (
            payload.characters[1].get("id") if len(payload.characters) > 1 else None
        ),
        "outcome_type": payload.outcome_type,
        "pressure_level": float(payload.beat.get("conflict_intensity") or 0.5),
        "scene_temperature": "warm",
    }
    shifts = shift_engine.compute(
        beat={**payload.beat, "outcome_type": payload.outcome_type},
        scene_drama=scene_drama,
        relationships=payload.relationships,
    )
    multidim_shifts = shift_engine.compute_multidim(
        beat={**payload.beat, "outcome_type": payload.outcome_type},
        scene_drama=scene_drama,
        relationships=payload.relationships,
    )

    return {
        "ok": True,
        "scene_id": scene_id,
        "outcome_type": payload.outcome_type,
        "updated_states": updated_states,
        "memory_traces": memory_traces,
        "power_shifts": shifts,
        "multidim_power_shifts": multidim_shifts,
    }


# ---------------------------------------------------------------------------
# ── Arcs ─────────────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

@router.get("/api/v1/drama/arcs/{character_id}")
def get_character_arc(character_id: str, project_id: str) -> dict[str, Any]:
    """Get the arc progress for a character (stub — DB lookup in production)."""
    return {"ok": True, "character_id": character_id, "project_id": project_id, "data": None}


@router.post("/api/v1/drama/arcs/{character_id}/advance")
def advance_character_arc(
    character_id: str, payload: ArcAdvanceRequest
) -> dict[str, Any]:
    """Advance a character's arc stage based on a scene outcome."""
    result = _arc_engine.evaluate(
        arc_progress={**payload.arc_progress, "character_id": character_id},
        scene_outcome=payload.scene_outcome,
        character_state=payload.character_state,
    )
    return {
        "ok": True,
        "character_id": character_id,
        "data": result,
    }


@router.post("/api/v1/drama/arcs/recompute")
def recompute_arcs(payload: ArcRecomputeRequest) -> dict[str, Any]:
    """Recompute arc progress for multiple characters from scene history."""
    results: list[dict[str, Any]] = []
    for char_id in payload.character_ids:
        arc_progress: dict[str, Any] = {"arc_stage": "mask_stable"}
        char_state: dict[str, Any] = {}
        for scene in payload.scene_history:
            outcome = str(scene.get("outcome_type") or "neutral")
            state_updates = scene.get("state_updates") or {}
            if char_id in state_updates:
                char_state = state_updates[char_id]
            arc_progress = _arc_engine.evaluate(
                arc_progress=arc_progress,
                scene_outcome=outcome,
                character_state=char_state,
            )
        results.append({"character_id": char_id, "arc": arc_progress})
    return {"ok": True, "data": results}


# ---------------------------------------------------------------------------
# ── Compile ───────────────────────────────────────────────────────────────────
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


@router.post("/api/v1/drama/compile/episode")
def compile_episode(payload: EpisodeCompileRequest) -> dict[str, Any]:
    """Compile all scenes in an episode sequentially, carrying state forward."""
    scene_results: list[dict[str, Any]] = []
    character_states: list[dict[str, Any]] = payload.arc_progresses or []
    memory_traces: list[dict[str, Any]] = list(payload.memory_traces)
    arc_progresses: list[dict[str, Any]] = []

    for scene in payload.scenes:
        beat = scene.get("beat") or scene
        scene_id = str(scene.get("scene_id") or scene.get("id") or f"scene_{len(scene_results)}")

        result = _compiler.compile(
            project_id=payload.project_id,
            scene_id=scene_id,
            episode_id=payload.episode_id,
            beat=beat,
            characters=payload.characters,
            character_states=character_states,
            relationships=payload.relationships,
            memory_traces=memory_traces,
            arc_progresses=arc_progresses,
        )
        scene_results.append(result)

        # Carry forward state
        for isu in result.get("inner_state_updates", []):
            updated = isu.get("updated_state") or {}
            cid = isu.get("character_id")
            if cid:
                character_states = [
                    s for s in character_states if s.get("character_id") != cid
                ]
                character_states.append({"character_id": cid, **updated})
            if isu.get("memory_trace"):
                memory_traces.append(isu["memory_trace"])

        arc_progresses = [
            {**au, "character_id": au.get("character_id")}
            for au in result.get("arc_updates", [])
        ]

    return {
        "ok": True,
        "project_id": payload.project_id,
        "episode_id": payload.episode_id,
        "scene_count": len(scene_results),
        "scenes": scene_results,
        "final_character_states": character_states,
        "arc_summary": arc_progresses,
    }


@router.post("/api/v1/drama/compile/project")
def compile_project(payload: ProjectCompileRequest) -> dict[str, Any]:
    """Compile all episodes in a project sequentially."""
    episode_results: list[dict[str, Any]] = []
    all_memory_traces: list[dict[str, Any]] = []
    carried_states: list[dict[str, Any]] = []
    arc_progresses: list[dict[str, Any]] = []

    for ep in payload.episodes:
        ep_id = str(ep.get("episode_id") or ep.get("id") or f"ep_{len(episode_results)}")
        ep_request = EpisodeCompileRequest(
            project_id=payload.project_id,
            episode_id=ep_id,
            scenes=ep.get("scenes") or [],
            characters=payload.characters,
            relationships=payload.relationships,
            memory_traces=all_memory_traces,
            arc_progresses=arc_progresses,
        )
        ep_result = compile_episode(ep_request)
        episode_results.append(ep_result)

        # Carry forward
        carried_states = ep_result.get("final_character_states") or carried_states
        arc_progresses = ep_result.get("arc_summary") or arc_progresses
        for s in ep_result.get("scenes") or []:
            for isu in s.get("inner_state_updates") or []:
                if isu.get("memory_trace"):
                    all_memory_traces.append(isu["memory_trace"])

    return {
        "ok": True,
        "project_id": payload.project_id,
        "episode_count": len(episode_results),
        "episodes": episode_results,
        "final_character_states": carried_states,
        "arc_summary": arc_progresses,
    }


# ---------------------------------------------------------------------------
# ── Legacy debug endpoints ───────────────────────────────────────────────────
# ---------------------------------------------------------------------------

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
    """Compute 7-component scene tension (section 8)."""
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
