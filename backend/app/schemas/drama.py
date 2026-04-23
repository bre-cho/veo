"""drama — Pydantic schemas for the Multi-Character Drama Engine.

Classes
-------
CharacterProfileSchema       — fixed character DNA
CharacterStateSchema         — per-scene mutable state
RelationshipEdgeSchema       — directed relationship between two characters
SceneDramaStateSchema        — drama analysis of a single scene
DialogueSubtextSchema        — spoken vs. real intent breakdown
PowerShiftSchema             — power delta from scene outcome
BlockingDirectiveSchema      — spatial/blocking instruction driven by drama
DramaArcSchema               — arc progression snapshot
DramaActingOutputSchema      — per-character acting decision for a scene
DramaCompileRequest          — full compile request payload
DramaCompileResponse         — full compile response payload
InnerStateUpdateSchema       — update applied after scene outcome
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Character
# ---------------------------------------------------------------------------

class CharacterProfileSchema(BaseModel):
    id: str | None = None
    project_id: str
    avatar_id: str | None = None
    name: str
    archetype: str = "observer"
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
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CharacterStateSchema(BaseModel):
    character_id: str
    project_id: str
    scene_id: str | None = None
    episode_id: str | None = None
    emotional_valence: float = 0.0
    arousal: float = 0.5
    control_level: float = 0.5
    dominance_level: float = 0.5
    vulnerability_level: float = 0.3
    trust_level: float = 0.5
    shame_level: float = 0.0
    anger_level: float = 0.0
    fear_level: float = 0.0
    desire_level: float = 0.3
    mask_strength: float = 0.7
    openness_level: float = 0.3
    internal_conflict_level: float = 0.0
    goal_pressure_level: float = 0.5
    current_subtext: str | None = None
    current_secret_load: float = 0.0
    current_power_position: str = "neutral"
    updated_from_previous_scene: bool = False


# ---------------------------------------------------------------------------
# Relationship
# ---------------------------------------------------------------------------

class RelationshipEdgeSchema(BaseModel):
    id: str | None = None
    project_id: str
    source_character_id: str
    target_character_id: str
    relation_type: str = "neutral"
    intimacy_level: float = 0.3
    trust_level: float = 0.5
    dependence_level: float = 0.0
    fear_level: float = 0.0
    resentment_level: float = 0.0
    attraction_level: float = 0.0
    rivalry_level: float = 0.0
    dominance_source_over_target: float = 0.5
    perceived_loyalty: float = 0.5
    hidden_agenda_score: float = 0.0
    recent_betrayal_score: float = 0.0
    unresolved_tension_score: float = 0.0
    status: str = "active"
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Scene drama
# ---------------------------------------------------------------------------

class SceneDramaStateSchema(BaseModel):
    scene_id: str
    project_id: str
    episode_id: str | None = None
    scene_goal: str | None = None
    visible_conflict: str | None = None
    hidden_conflict: str | None = None
    scene_temperature: str = "neutral"
    pressure_level: float = 0.5
    dominant_character_id: str | None = None
    threatened_character_id: str | None = None
    emotional_center_character_id: str | None = None
    key_secret_in_play: str | None = None
    scene_turning_point: str | None = None
    outcome_type: str = "neutral"
    power_shift_delta: float = 0.0
    trust_shift_delta: float = 0.0
    exposure_shift_delta: float = 0.0
    dependency_shift_delta: float = 0.0
    scene_aftertaste: str | None = None


# ---------------------------------------------------------------------------
# Dialogue subtext
# ---------------------------------------------------------------------------

class DialogueSubtextSchema(BaseModel):
    character_id: str
    spoken_line: str | None = None
    spoken_intent: str
    real_intent: str
    subtext_label: str
    suppressed_emotion: str | None = None
    power_move: str | None = None


# ---------------------------------------------------------------------------
# Power shift
# ---------------------------------------------------------------------------

class PowerShiftSchema(BaseModel):
    scene_id: str
    from_character_id: str
    to_character_id: str
    shift_type: str  # e.g. "dominance_transfer", "trust_collapse", "exposure"
    magnitude: float = 0.0
    trigger_event: str | None = None
    camera_cue: str | None = None


# ---------------------------------------------------------------------------
# Blocking
# ---------------------------------------------------------------------------

class BlockingDirectiveSchema(BaseModel):
    scene_id: str
    character_id: str
    spatial_position: str | None = None  # e.g. "foreground_left"
    facing_direction: str | None = None
    distance_from_target: str | None = None  # "close", "medium", "far"
    movement_cue: str | None = None
    camera_angle_preference: str | None = None
    shot_type_preference: str | None = None
    drama_reason: str | None = None


# ---------------------------------------------------------------------------
# Arc
# ---------------------------------------------------------------------------

class DramaArcSchema(BaseModel):
    character_id: str
    project_id: str
    episode_id: str | None = None
    arc_name: str = "main"
    arc_stage: str = "ordinary_world"
    false_belief: str | None = None
    pressure_index: float = 0.0
    transformation_index: float = 0.0
    collapse_risk: float = 0.0
    mask_break_level: float = 0.0
    truth_acceptance_level: float = 0.0
    relation_entanglement_index: float = 0.0


# ---------------------------------------------------------------------------
# Per-character acting output (drama-aware)
# ---------------------------------------------------------------------------

class DramaActingOutputSchema(BaseModel):
    character_id: str
    scene_id: str
    emotion_state: CharacterStateSchema
    scene_goal: str
    subtext: str
    reaction_pattern: str
    micro_expression: str
    body_language: str
    line_delivery: dict[str, str] = Field(default_factory=dict)
    power_position: str = "neutral"
    camera_directive: BlockingDirectiveSchema | None = None


# ---------------------------------------------------------------------------
# Inner state update (applied after scene resolves)
# ---------------------------------------------------------------------------

class InnerStateUpdateSchema(BaseModel):
    """Deltas to apply to a character's state after a scene outcome."""

    character_id: str
    scene_id: str
    outcome_type: str  # "betrayal", "victory", "exposure", "confession", etc.
    emotional_state_delta: dict[str, float] = Field(default_factory=dict)
    relationship_deltas: dict[str, dict[str, float]] = Field(default_factory=dict)
    new_memory_trace: dict[str, Any] | None = None
    arc_stage_update: str | None = None


# ---------------------------------------------------------------------------
# Compile request / response
# ---------------------------------------------------------------------------

class DramaCompileRequest(BaseModel):
    """Input to the DramaCompilerService."""

    project_id: str
    scene_id: str
    episode_id: str | None = None
    beat: dict[str, Any]
    characters: list[CharacterProfileSchema]
    character_states: list[CharacterStateSchema] = Field(default_factory=list)
    relationships: list[RelationshipEdgeSchema] = Field(default_factory=list)
    memory_traces: list[dict[str, Any]] = Field(default_factory=list)


class DramaCompileResponse(BaseModel):
    """Full drama output for a scene."""

    ok: bool = True
    scene_drama: SceneDramaStateSchema
    character_acting: list[DramaActingOutputSchema] = Field(default_factory=list)
    power_shifts: list[PowerShiftSchema] = Field(default_factory=list)
    blocking_directives: list[BlockingDirectiveSchema] = Field(default_factory=list)
    dialogue_subtexts: list[DialogueSubtextSchema] = Field(default_factory=list)
    arc_updates: list[DramaArcSchema] = Field(default_factory=list)
    inner_state_updates: list[InnerStateUpdateSchema] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
