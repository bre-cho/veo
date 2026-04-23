-- schema.sql
-- Avatar Tournament + Avatar Governance
-- Postgres-oriented additive schema
-- Safe pattern: add tables/indexes first, wire code later

BEGIN;

CREATE TABLE IF NOT EXISTS avatar_tournament_runs (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    project_id UUID NULL,
    topic_signature TEXT NULL,
    template_family TEXT NULL,
    platform TEXT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    selection_mode VARCHAR(32) NOT NULL DEFAULT 'exploit',
    exploration_ratio NUMERIC(6,4) NOT NULL DEFAULT 0.1500,
    selected_avatar_id UUID NULL,
    selected_template_id UUID NULL,
    baseline_avatar_id UUID NULL,
    started_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    context_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_avatar_tournament_runs_workspace_created
    ON avatar_tournament_runs (workspace_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_avatar_tournament_runs_project
    ON avatar_tournament_runs (project_id);

CREATE INDEX IF NOT EXISTS idx_avatar_tournament_runs_status
    ON avatar_tournament_runs (status);

CREATE TABLE IF NOT EXISTS avatar_match_results (
    id UUID PRIMARY KEY,
    tournament_run_id UUID NOT NULL REFERENCES avatar_tournament_runs(id) ON DELETE CASCADE,
    avatar_id UUID NOT NULL,
    template_id UUID NULL,
    topic_signature TEXT NULL,
    platform TEXT NULL,

    predicted_score NUMERIC(8,4) NULL,
    predicted_ctr NUMERIC(8,4) NULL,
    predicted_retention NUMERIC(8,4) NULL,
    predicted_conversion NUMERIC(8,4) NULL,
    continuity_score NUMERIC(8,4) NULL,
    brand_fit_score NUMERIC(8,4) NULL,
    pair_fit_score NUMERIC(8,4) NULL,
    governance_penalty NUMERIC(8,4) NULL,
    exploration_bonus NUMERIC(8,4) NULL,
    final_rank_score NUMERIC(8,4) NULL,

    actual_ctr NUMERIC(8,4) NULL,
    actual_retention NUMERIC(8,4) NULL,
    actual_watch_time NUMERIC(12,4) NULL,
    actual_conversion NUMERIC(8,4) NULL,
    actual_publish_score NUMERIC(8,4) NULL,
    actual_engagement_score NUMERIC(8,4) NULL,
    actual_continuity_health NUMERIC(8,4) NULL,

    fitness_score NUMERIC(8,4) NULL,
    result_label VARCHAR(32) NULL,
    selection_rank INTEGER NULL,
    was_published BOOLEAN NOT NULL DEFAULT FALSE,
    was_exploration BOOLEAN NOT NULL DEFAULT FALSE,
    notes_json JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_avatar_match_results_tournament
    ON avatar_match_results (tournament_run_id);

CREATE INDEX IF NOT EXISTS idx_avatar_match_results_avatar_created
    ON avatar_match_results (avatar_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_avatar_match_results_avatar_template
    ON avatar_match_results (avatar_id, template_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_avatar_match_results_topic_platform
    ON avatar_match_results (topic_signature, platform, created_at DESC);

CREATE TABLE IF NOT EXISTS avatar_policy_states (
    id UUID PRIMARY KEY,
    avatar_id UUID NOT NULL UNIQUE,
    state VARCHAR(32) NOT NULL DEFAULT 'candidate',
    priority_weight NUMERIC(8,4) NOT NULL DEFAULT 1.0000,
    exploration_weight NUMERIC(8,4) NOT NULL DEFAULT 0.1500,
    risk_weight NUMERIC(8,4) NOT NULL DEFAULT 0.0000,
    continuity_confidence NUMERIC(8,4) NULL,
    quality_confidence NUMERIC(8,4) NULL,
    recent_win_rate NUMERIC(8,4) NULL,
    recent_loss_rate NUMERIC(8,4) NULL,
    cooldown_until TIMESTAMPTZ NULL,
    last_promotion_at TIMESTAMPTZ NULL,
    last_demotion_at TIMESTAMPTZ NULL,
    last_rollback_at TIMESTAMPTZ NULL,
    stable_pair_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    notes_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_avatar_policy_states_state
    ON avatar_policy_states (state);

CREATE INDEX IF NOT EXISTS idx_avatar_policy_states_cooldown
    ON avatar_policy_states (cooldown_until);

CREATE TABLE IF NOT EXISTS avatar_promotion_events (
    id UUID PRIMARY KEY,
    avatar_id UUID NOT NULL,
    tournament_run_id UUID NULL REFERENCES avatar_tournament_runs(id) ON DELETE SET NULL,
    event_type VARCHAR(32) NOT NULL,
    from_state VARCHAR(32) NULL,
    to_state VARCHAR(32) NULL,
    reason_code VARCHAR(64) NOT NULL,
    reason_text TEXT NULL,
    source_metric_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_avatar_promotion_events_avatar_created
    ON avatar_promotion_events (avatar_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_avatar_promotion_events_type
    ON avatar_promotion_events (event_type, created_at DESC);

CREATE TABLE IF NOT EXISTS avatar_guardrail_events (
    id UUID PRIMARY KEY,
    avatar_id UUID NOT NULL,
    project_id UUID NULL,
    tournament_run_id UUID NULL REFERENCES avatar_tournament_runs(id) ON DELETE SET NULL,
    guardrail_code VARCHAR(64) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    action_taken VARCHAR(32) NOT NULL DEFAULT 'none',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_avatar_guardrail_events_avatar_created
    ON avatar_guardrail_events (avatar_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_avatar_guardrail_events_code
    ON avatar_guardrail_events (guardrail_code, created_at DESC);

-- Optional helper view for latest avatar state + recent metrics
CREATE OR REPLACE VIEW avatar_governance_overview AS
SELECT
    aps.avatar_id,
    aps.state,
    aps.priority_weight,
    aps.exploration_weight,
    aps.risk_weight,
    aps.continuity_confidence,
    aps.quality_confidence,
    aps.recent_win_rate,
    aps.recent_loss_rate,
    aps.cooldown_until,
    aps.updated_at AS policy_updated_at
FROM avatar_policy_states aps;

COMMIT;
