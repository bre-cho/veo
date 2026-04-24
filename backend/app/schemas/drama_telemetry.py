"""drama_telemetry — Pydantic schemas for the Drama Telemetry / Scorecard system.

Scene-level, character-level and episode-level metrics used by the Drama Engine
to self-learn and evaluate scene quality.

Classes
-------
SceneTelemetrySchema       — per-scene quality metrics
CharacterTelemetrySchema   — per-character arc & expression metrics
EpisodeTelemetrySchema     — episode-wide continuity and drama metrics
DramaTelemetryReport       — full report bundling all three levels
RenderBridgeActingSchema   — acting parameters for one character in render bridge output
RenderBridgeRelationshipShiftSchema — relationship delta entry in render bridge output
RenderBridgeCameraPlanSchema        — camera plan in render bridge output
RenderBridgeBlockingPlanSchema      — blocking plan in render bridge output
RenderBridgeOutputSchema   — full render bridge output format (item 25)
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Scene-level telemetry
# ---------------------------------------------------------------------------

class SceneTelemetrySchema(BaseModel):
    """Per-scene quality metrics that feed the self-learning system."""

    scene_id: str
    project_id: str
    episode_id: str | None = None

    # Core drama quality metrics (0–100)
    tension_score: float = 0.0
    power_shift_magnitude: float = 0.0
    trust_shift_magnitude: float = 0.0
    exposure_risk_score: float = 0.0
    subtext_density: float = 0.0
    chemistry_score: float = 0.0
    continuity_integrity_score: float = 0.0

    # Computed aggregates
    total_scene_score: float = 0.0
    scene_grade: str = "normal"  # "peak" | "strong" | "normal" | "flat"

    # Anti-fake-drama flags
    fake_drama_violations: list[str] = Field(default_factory=list)

    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Character-level telemetry
# ---------------------------------------------------------------------------

class CharacterTelemetrySchema(BaseModel):
    """Per-character arc and expressive quality metrics."""

    character_id: str
    scene_id: str
    project_id: str

    arc_momentum: float = 0.0           # how much the arc advanced this scene
    mask_break_progress: float = 0.0    # cumulative mask erosion (0=intact, 1=fully broken)
    emotional_variation_range: float = 0.0  # spread of emotions expressed
    relation_complexity_index: float = 0.0  # mean edge-weight complexity in scene

    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Episode-level telemetry
# ---------------------------------------------------------------------------

class EpisodeTelemetrySchema(BaseModel):
    """Episode-wide continuity and dramatic arc metrics."""

    project_id: str
    episode_id: str

    betrayal_count: int = 0
    alliance_flip_count: int = 0
    unresolved_tension_load: float = 0.0    # mean unresolved tension across scenes
    emotional_continuity_quality: float = 0.0  # 0–1, how consistent emotion arcs are
    dominant_relationship_arc_strength: float = 0.0  # strength of the primary relationship arc

    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Full telemetry report
# ---------------------------------------------------------------------------

class DramaTelemetryReport(BaseModel):
    """Bundles scene, character and episode telemetry into one report."""

    ok: bool = True
    scene: SceneTelemetrySchema
    characters: list[CharacterTelemetrySchema] = Field(default_factory=list)
    episode: EpisodeTelemetrySchema | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Render bridge output (item 25)
# ---------------------------------------------------------------------------

class RenderBridgeActingSchema(BaseModel):
    """Acting parameters for a single character in the render bridge output."""

    character_id: str
    emotion: dict[str, float] = Field(default_factory=dict)
    acting: dict[str, str] = Field(default_factory=dict)


class RenderBridgeRelationshipShiftSchema(BaseModel):
    """Relationship delta entry in render bridge output."""

    source: str
    target: str
    trust_delta: float = 0.0
    resentment_delta: float = 0.0
    dominance_delta: float = 0.0
    fear_delta: float = 0.0
    hidden_agenda_delta: float = 0.0
    shame_delta: float = 0.0


class RenderBridgeCameraPlanSchema(BaseModel):
    """Camera plan in render bridge output."""

    mode: str = "neutral"
    focus_order: list[str] = Field(default_factory=list)
    movement: str | None = None
    framing: str | None = None


class RenderBridgeBlockingPlanSchema(BaseModel):
    """Per-character blocking instructions in render bridge output."""

    character_id: str
    blocking: str | None = None


class RenderBridgeOutputSchema(BaseModel):
    """Full render bridge output format (item 25).

    This is the payload injected into the render pipeline after the Drama Engine
    compiles a scene.  It contains everything the Avatar Acting Model and camera
    planner need to render the scene correctly.
    """

    scene_id: str
    drama_state: dict[str, Any] = Field(default_factory=dict)
    character_updates: list[RenderBridgeActingSchema] = Field(default_factory=list)
    relationship_shifts: list[RenderBridgeRelationshipShiftSchema] = Field(default_factory=list)
    camera_plan: RenderBridgeCameraPlanSchema = Field(default_factory=RenderBridgeCameraPlanSchema)
    blocking_plan: list[RenderBridgeBlockingPlanSchema] = Field(default_factory=list)
    fake_drama_violations: list[str] = Field(default_factory=list)
    telemetry: SceneTelemetrySchema | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
