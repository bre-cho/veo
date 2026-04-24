"""drama — Pydantic schemas for the Multi-Character Drama Engine.

Classes
-------
CharacterProfileSchema           — fixed character DNA
CharacterStateSchema             — per-scene mutable state
RelationshipEdgeSchema           — directed relationship between two characters
SceneDramaStateSchema            — drama analysis of a single scene
SceneTensionSchema               — 7-component tension breakdown + flat_scene flag
DialogueSubtextSchema            — spoken vs. real intent breakdown (3-layer)
DialogueSubtextFullSchema        — full per-line subtext record (section 9.3)
MultiDimensionalPowerShiftSchema — 6-axis power shift (section 10.3)
PowerShiftSchema                 — legacy single-axis power shift
BlockingDirectiveSchema          — spatial/blocking instruction driven by drama
BlockingPlanSchema               — full scene blocking plan (section 14)
CameraDramaPlanSchema            — full camera psychology plan (section 15.2)
DramaArcSchema                   — arc progression snapshot (drama stages, section 16)
ChemistrySchema                  — multi-dimension chemistry between two characters (section 13)
BetrayalAllianceSchema           — alliance state + betrayal probability (section 12)
DramaActingOutputSchema          — per-character acting decision for a scene
DramaCompileRequest              — full compile request payload
DramaCompileResponse             — full compile response payload
InnerStateUpdateSchema           — update applied after scene outcome
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
    """Directed A → B relationship edge with full edge scores.

    Relation types (section 7.1): mentor, rival, superior, subordinate, ally,
    enemy, protector, dependent, pursuer, avoidant, ex-trust, covert-attraction,
    manipulator-target, shared-secret, betrayer-betrayed.

    Edge scores (section 7.2): all 0–1 scale from the perspective of the
    *source* character toward the *target*.
    """

    id: str | None = None
    project_id: str
    source_character_id: str
    target_character_id: str
    relation_type: str = "neutral"

    # Core edge scores (section 7.2)
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

    # Legacy / derived fields kept for backwards compat
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
# Scene tension (7-component formula, section 8)
# ---------------------------------------------------------------------------

class SceneTensionSchema(BaseModel):
    """7-component tension score (section 8.3).

    Each component is 0–1. ``tension_score`` is the weighted sum normalised
    to 0–100.  ``flat_scene`` is raised when the scene has no meaningful
    collision, risk, or shift.
    """

    scene_temperature: str = "neutral"
    pressure_level: float = 0.5
    tension_score: float = 50.0  # 0–100 normalised

    goal_collision: float = 0.0
    hidden_agenda_asymmetry: float = 0.0
    emotional_exposure_risk: float = 0.0
    power_imbalance: float = 0.0
    unresolved_prior_memory: float = 0.0
    time_pressure: float = 0.0
    social_consequence: float = 0.0

    tension_sources: list[str] = Field(default_factory=list)
    dominant_tension_type: str = "latent"
    flat_scene: bool = False


# ---------------------------------------------------------------------------
# Dialogue subtext (3-layer, section 9)
# ---------------------------------------------------------------------------

class DialogueSubtextSchema(BaseModel):
    character_id: str
    spoken_line: str | None = None
    spoken_intent: str
    real_intent: str
    subtext_label: str
    suppressed_emotion: str | None = None
    power_move: str | None = None


class DialogueSubtextFullSchema(BaseModel):
    """Full 3-layer per-line subtext record (section 9.3)."""

    id: str | None = None
    scene_id: str
    speaker_id: str
    target_id: str | None = None

    line_text: str | None = None
    literal_intent: str | None = None
    hidden_intent: str | None = None
    psychological_action: str | None = None

    # Dialogue act type (section 9.2)
    dialogue_act: str = "direct"  # attack / probe / withhold / seduce / shame /
    #   reassure / dominate / retreat / bait / confess / redirect / expose /
    #   deny / test_loyalty

    # Charge dimensions (0–1)
    emotional_charge: float = 0.5
    honesty_level: float = 0.5
    mask_level: float = 0.5
    threat_level: float = 0.0
    intimacy_bid: float = 0.0
    power_move: str | None = None
    expected_target_reaction: str | None = None


# ---------------------------------------------------------------------------
# Multi-dimensional power shift (section 10)
# ---------------------------------------------------------------------------

class MultiDimensionalPowerShiftSchema(BaseModel):
    """6-axis power shift record (section 10.3)."""

    scene_id: str
    from_character_id: str
    to_character_id: str

    social_delta: float = 0.0
    emotional_delta: float = 0.0
    informational_delta: float = 0.0
    moral_delta: float = 0.0
    spatial_delta: float = 0.0
    narrative_control_delta: float = 0.0

    trigger_event: str | None = None
    explanation: str | None = None


# ---------------------------------------------------------------------------
# Power shift (legacy single-axis kept for compile response)
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


class BlockingPlanSchema(BaseModel):
    """Full scene blocking plan (section 14)."""

    scene_id: str
    character_directives: list[BlockingDirectiveSchema] = Field(default_factory=list)

    # Scene-level blocking cues
    distance_change: str | None = None          # "closing" / "widening"
    who_steps_first: str | None = None           # character_id
    who_turns_away_first: str | None = None
    who_sits: str | None = None
    who_controls_exit: str | None = None
    who_occupies_center: str | None = None
    who_is_cornered: str | None = None
    blocking_notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Camera drama plan (section 15)
# ---------------------------------------------------------------------------

class CameraDramaPlanSchema(BaseModel):
    """Full camera psychology plan (section 15.2)."""

    scene_id: str
    character_focus_priority: list[str] = Field(default_factory=list)
    emotional_anchor_character_id: str | None = None
    dominant_visual_axis: str | None = None

    # Lens psychology mode (section 15.3 examples mapped to slugs)
    lens_psychology_mode: str | None = None  # pressure / alienation / instability / dread
    framing_mode: str | None = None          # tight / wide / off-centre / over-shoulder
    eye_line_strategy: str | None = None     # dominant / subordinate / avoidant / locked

    reveal_timing: str | None = None         # immediate / delayed / withheld
    pause_hold_strategy: str | None = None
    movement_strategy: str | None = None     # creeping_push / static / drift / pull_back

    blocking_sync_notes: str | None = None
    continuity_notes: str | None = None
    shot_sequence: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Arc (drama-specific stages, section 16)
# ---------------------------------------------------------------------------

class DramaArcSchema(BaseModel):
    """Arc progression snapshot with drama-specific stages (section 16.1).

    Stages: mask_stable → pressure_crack → defensive_escalation →
    first_exposure → collapse_rupture → truth_encounter →
    reorganization → transformed_state
    """

    character_id: str
    project_id: str
    episode_id: str | None = None
    arc_name: str = "main"

    # Drama arc stages (section 16.1)
    arc_stage: str = "mask_stable"
    arc_type: str | None = None  # section 16.2 e.g. "control_to_vulnerability"

    false_belief: str | None = None
    pressure_index: float = 0.0
    transformation_index: float = 0.0
    collapse_risk: float = 0.0
    mask_break_level: float = 0.0
    truth_acceptance_level: float = 0.0
    relation_entanglement_index: float = 0.0
    false_belief_challenge_level: float = 0.0


# ---------------------------------------------------------------------------
# Chemistry (section 13)
# ---------------------------------------------------------------------------

class ChemistrySchema(BaseModel):
    """Multi-dimension chemistry between two characters (section 13)."""

    source_character_id: str
    target_character_id: str

    tempo_compatibility: float = 0.5       # 0 = mismatch, 1 = sync
    eye_contact_tolerance: float = 0.5
    interruption_rhythm: float = 0.5       # 0 = one overrides, 1 = mutual
    mutual_reading_accuracy: float = 0.5
    emotional_danger: float = 0.0
    attraction_vs_fear_blend: float = 0.5  # 0 = pure fear, 1 = pure attraction
    speech_completion_tendency: float = 0.5
    silence_comfort_index: float = 0.5

    chemistry_score: float = 0.0
    chemistry_type: str = "neutral"        # forbidden_tension / power_clash / mutual_pull / etc.
    tension_type: str = "latent"


# ---------------------------------------------------------------------------
# Betrayal / Alliance (section 12)
# ---------------------------------------------------------------------------

class BetrayalAllianceSchema(BaseModel):
    """Alliance state + betrayal probability between two characters (section 12)."""

    source_character_id: str
    target_character_id: str

    # Alliance state (section 12.1)
    alliance_state: str | None = None  # tactical / emotional / conditional /
    #   dependency_based / secret / none

    # Betrayal state (section 12.2)
    betrayal_state: str | None = None  # overt / passive / loyalty_failure /
    #   self_protection / ideological / none

    betrayal_probability: float = 0.0   # 0–1
    reconciliation_probability: float = 0.5
    alliance_strength: float = 0.5      # 0 = broken, 1 = solid
    future_tension_seed: str | None = None
    trigger_reason: str | None = None


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
    tension_analysis: SceneTensionSchema | None = None
    character_acting: list[DramaActingOutputSchema] = Field(default_factory=list)
    power_shifts: list[PowerShiftSchema] = Field(default_factory=list)
    multidim_power_shifts: list[MultiDimensionalPowerShiftSchema] = Field(default_factory=list)
    blocking_directives: list[BlockingDirectiveSchema] = Field(default_factory=list)
    blocking_plan: BlockingPlanSchema | None = None
    camera_plan: CameraDramaPlanSchema | None = None
    dialogue_subtexts: list[DialogueSubtextFullSchema] = Field(default_factory=list)
    arc_updates: list[DramaArcSchema] = Field(default_factory=list)
    inner_state_updates: list[InnerStateUpdateSchema] = Field(default_factory=list)
    chemistry_map: list[ChemistrySchema] = Field(default_factory=list)
    betrayal_alliance_map: list[BetrayalAllianceSchema] = Field(default_factory=list)
    scene_law_violations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
