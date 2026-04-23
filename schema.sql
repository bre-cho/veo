-- MULTI_CHARACTER_DRAMA_ENGINE — schema.sql
-- PostgreSQL-oriented additive patch
-- Safe additive merge: no destructive changes to existing render core

BEGIN;

CREATE TABLE IF NOT EXISTS drama_character_profiles (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL,
    external_avatar_id UUID NULL,
    name VARCHAR(255) NOT NULL,
    archetype VARCHAR(100) NOT NULL,
    public_persona TEXT NULL,
    private_self TEXT NULL,
    outer_goal TEXT NULL,
    hidden_need TEXT NULL,
    core_wound TEXT NULL,
    dominant_fear TEXT NULL,
    mask_strategy TEXT NULL,
    pressure_response VARCHAR(120) NULL,
    speech_pattern TEXT NULL,
    movement_pattern TEXT NULL,
    gaze_pattern TEXT NULL,
    tempo_default VARCHAR(50) NULL,
    status_default VARCHAR(50) NULL,
    attachment_style VARCHAR(50) NULL,
    dominance_baseline NUMERIC(5,2) NOT NULL DEFAULT 0.50,
    trust_baseline NUMERIC(5,2) NOT NULL DEFAULT 0.50,
    openness_baseline NUMERIC(5,2) NOT NULL DEFAULT 0.50,
    volatility_baseline NUMERIC(5,2) NOT NULL DEFAULT 0.50,
    acting_preset_seed JSONB NOT NULL DEFAULT '{}'::jsonb,
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS drama_character_states (
    id UUID PRIMARY KEY,
    character_id UUID NOT NULL REFERENCES drama_character_profiles(id) ON DELETE CASCADE,
    scene_id UUID NOT NULL,
    episode_id UUID NULL,
    emotional_valence NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    arousal NUMERIC(5,2) NOT NULL DEFAULT 0.50,
    control_level NUMERIC(5,2) NOT NULL DEFAULT 0.50,
    dominance_level NUMERIC(5,2) NOT NULL DEFAULT 0.50,
    vulnerability_level NUMERIC(5,2) NOT NULL DEFAULT 0.50,
    trust_level NUMERIC(5,2) NOT NULL DEFAULT 0.50,
    shame_level NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    anger_level NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    fear_level NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    desire_level NUMERIC(5,2) NOT NULL DEFAULT 0.50,
    mask_strength NUMERIC(5,2) NOT NULL DEFAULT 0.50,
    openness_level NUMERIC(5,2) NOT NULL DEFAULT 0.50,
    internal_conflict_level NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    goal_pressure_level NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    current_subtext TEXT NULL,
    current_secret_load NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    current_power_position VARCHAR(50) NULL,
    updated_from_previous_scene BOOLEAN NOT NULL DEFAULT FALSE,
    source_scene_state_id UUID NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(character_id, scene_id)
);

CREATE TABLE IF NOT EXISTS drama_relationship_edges (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL,
    source_character_id UUID NOT NULL REFERENCES drama_character_profiles(id) ON DELETE CASCADE,
    target_character_id UUID NOT NULL REFERENCES drama_character_profiles(id) ON DELETE CASCADE,
    relation_type VARCHAR(100) NOT NULL,
    intimacy_level NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    trust_level NUMERIC(5,2) NOT NULL DEFAULT 0.50,
    dependence_level NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    fear_level NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    resentment_level NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    attraction_level NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    rivalry_level NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    moral_superiority_level NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    perceived_power NUMERIC(5,2) NOT NULL DEFAULT 0.50,
    hidden_agenda_score NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    shame_exposure_risk NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    emotional_hook_strength NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    dominance_source_over_target NUMERIC(5,2) NOT NULL DEFAULT 0.50,
    perceived_loyalty NUMERIC(5,2) NOT NULL DEFAULT 0.50,
    recent_betrayal_score NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    unresolved_tension_score NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(project_id, source_character_id, target_character_id)
);

CREATE TABLE IF NOT EXISTS drama_scene_states (
    id UUID PRIMARY KEY,
    scene_id UUID NOT NULL UNIQUE,
    project_id UUID NOT NULL,
    episode_id UUID NULL,
    scene_goal TEXT NULL,
    visible_conflict TEXT NULL,
    hidden_conflict TEXT NULL,
    scene_temperature NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    pressure_level NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    exposure_risk_score NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    time_pressure_score NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    social_consequence_score NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    tension_score NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    flat_scene_flag BOOLEAN NOT NULL DEFAULT FALSE,
    dominant_character_id UUID NULL REFERENCES drama_character_profiles(id),
    threatened_character_id UUID NULL REFERENCES drama_character_profiles(id),
    emotional_center_character_id UUID NULL REFERENCES drama_character_profiles(id),
    key_secret_in_play TEXT NULL,
    scene_turning_point TEXT NULL,
    outcome_type VARCHAR(100) NULL,
    power_shift_delta JSONB NOT NULL DEFAULT '{}'::jsonb,
    trust_shift_delta JSONB NOT NULL DEFAULT '{}'::jsonb,
    exposure_shift_delta JSONB NOT NULL DEFAULT '{}'::jsonb,
    dependency_shift_delta JSONB NOT NULL DEFAULT '{}'::jsonb,
    scene_aftertaste TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS drama_dialogue_subtexts (
    id UUID PRIMARY KEY,
    scene_id UUID NOT NULL,
    speaker_id UUID NOT NULL REFERENCES drama_character_profiles(id) ON DELETE CASCADE,
    target_id UUID NULL REFERENCES drama_character_profiles(id) ON DELETE SET NULL,
    line_index INTEGER NOT NULL,
    line_text TEXT NOT NULL,
    literal_intent VARCHAR(120) NULL,
    hidden_intent VARCHAR(120) NULL,
    psychological_action VARCHAR(120) NULL,
    emotional_charge NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    honesty_level NUMERIC(5,2) NOT NULL DEFAULT 0.50,
    mask_level NUMERIC(5,2) NOT NULL DEFAULT 0.50,
    threat_level NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    intimacy_bid NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    power_move VARCHAR(120) NULL,
    expected_target_reaction VARCHAR(120) NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS drama_power_shifts (
    id UUID PRIMARY KEY,
    scene_id UUID NOT NULL,
    from_character_id UUID NOT NULL REFERENCES drama_character_profiles(id) ON DELETE CASCADE,
    to_character_id UUID NOT NULL REFERENCES drama_character_profiles(id) ON DELETE CASCADE,
    social_delta NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    emotional_delta NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    informational_delta NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    moral_delta NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    spatial_delta NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    narrative_control_delta NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    trigger_event VARCHAR(120) NULL,
    explanation TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS drama_memory_traces (
    id UUID PRIMARY KEY,
    character_id UUID NOT NULL REFERENCES drama_character_profiles(id) ON DELETE CASCADE,
    related_character_id UUID NULL REFERENCES drama_character_profiles(id) ON DELETE SET NULL,
    source_scene_id UUID NOT NULL,
    event_type VARCHAR(120) NOT NULL,
    emotional_weight NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    trust_impact NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    shame_impact NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    fear_impact NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    dominance_impact NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    meaning_label VARCHAR(120) NULL,
    decay_rate NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    persistence_score NUMERIC(5,2) NOT NULL DEFAULT 0.50,
    recall_trigger VARCHAR(255) NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS drama_arc_progress (
    id UUID PRIMARY KEY,
    character_id UUID NOT NULL REFERENCES drama_character_profiles(id) ON DELETE CASCADE,
    episode_id UUID NULL,
    arc_name VARCHAR(255) NOT NULL,
    arc_stage VARCHAR(80) NOT NULL,
    false_belief TEXT NULL,
    pressure_index NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    transformation_index NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    collapse_risk NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    mask_break_level NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    truth_acceptance_level NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    relation_entanglement_index NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS drama_blocking_plans (
    id UUID PRIMARY KEY,
    scene_id UUID NOT NULL UNIQUE,
    project_id UUID NOT NULL,
    emotional_anchor_character_id UUID NULL REFERENCES drama_character_profiles(id),
    center_frame_owner_id UUID NULL REFERENCES drama_character_profiles(id),
    doorway_owner_id UUID NULL REFERENCES drama_character_profiles(id),
    distance_strategy VARCHAR(120) NULL,
    eye_line_strategy VARCHAR(120) NULL,
    body_orientation_strategy VARCHAR(120) NULL,
    movement_pressure_strategy VARCHAR(120) NULL,
    entry_exit_control_notes TEXT NULL,
    power_geometry_notes TEXT NULL,
    beat_map JSONB NOT NULL DEFAULT '[]'::jsonb,
    continuity_notes TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS drama_camera_plans (
    id UUID PRIMARY KEY,
    scene_id UUID NOT NULL UNIQUE,
    project_id UUID NOT NULL,
    character_focus_priority JSONB NOT NULL DEFAULT '[]'::jsonb,
    emotional_anchor_character_id UUID NULL REFERENCES drama_character_profiles(id),
    dominant_visual_axis VARCHAR(120) NULL,
    lens_psychology_mode VARCHAR(120) NULL,
    framing_mode VARCHAR(120) NULL,
    eye_line_strategy VARCHAR(120) NULL,
    reveal_timing VARCHAR(120) NULL,
    pause_hold_strategy VARCHAR(120) NULL,
    movement_strategy VARCHAR(120) NULL,
    transition_strategy VARCHAR(120) NULL,
    lighting_strategy VARCHAR(120) NULL,
    shot_duration_hint_seconds NUMERIC(5,2) NULL,
    blocking_sync_notes TEXT NULL,
    continuity_notes TEXT NULL,
    source_ruleset VARCHAR(120) NOT NULL DEFAULT 'hollywood_psychology_v1',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dcp_project ON drama_character_profiles(project_id);
CREATE INDEX IF NOT EXISTS idx_dcs_character_scene ON drama_character_states(character_id, scene_id);
CREATE INDEX IF NOT EXISTS idx_dre_project_source_target ON drama_relationship_edges(project_id, source_character_id, target_character_id);
CREATE INDEX IF NOT EXISTS idx_dss_project_episode ON drama_scene_states(project_id, episode_id);
CREATE INDEX IF NOT EXISTS idx_dds_scene ON drama_dialogue_subtexts(scene_id, line_index);
CREATE INDEX IF NOT EXISTS idx_dps_scene ON drama_power_shifts(scene_id);
CREATE INDEX IF NOT EXISTS idx_dmt_character_related ON drama_memory_traces(character_id, related_character_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_dap_character_episode ON drama_arc_progress(character_id, episode_id);
CREATE INDEX IF NOT EXISTS idx_dbp_project_scene ON drama_blocking_plans(project_id, scene_id);
CREATE INDEX IF NOT EXISTS idx_dcam_project_scene ON drama_camera_plans(project_id, scene_id);

ALTER TABLE drama_relationship_edges
    ADD CONSTRAINT chk_dre_not_self CHECK (source_character_id <> target_character_id);

COMMIT;
