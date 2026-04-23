"""Router registry – groups all API routers by domain.

Import ``register_all_routers`` and call it with the FastAPI app instance
instead of listing every router in ``main.py``.  This keeps ``main.py`` thin
and avoids merge conflicts when new routers are added.
"""
from __future__ import annotations

from fastapi import FastAPI

# ── Core / infrastructure ──────────────────────────────────────────────────
from app.api.health import router as health_router
from app.api.storage import router as storage_router
from app.api.google_accounts import router as google_accounts_router
from app.api.observability import router as observability_router

# ── Script / preview pipeline ─────────────────────────────────────────────
from app.api.script_upload_preview import router as script_upload_preview_router
from app.api.script_validation import router as script_validation_router
from app.api.script_regeneration_routes import router as script_regeneration_router
from app.api.provider_payload_preview import router as provider_payload_preview_router
from app.api.topic_intake import router as topic_intake_router

# ── Project workspace ─────────────────────────────────────────────────────
from app.api.project_from_preview import router as project_from_preview_router
from app.api.project_workspace import router as project_workspace_router
from app.api.veo_workspace import router as veo_workspace_router

# ── Render execution ──────────────────────────────────────────────────────
from app.api.render_execution import router as render_execution_router
from app.api.render_job_status import router as render_job_status_router
from app.api.render_dashboard import router as render_dashboard_router
from app.api.render_job_health import router as render_job_health_router
from app.api.render_events import router as render_events_router
from app.api.provider_callbacks import router as provider_callbacks_router

# ── Orchestration / control ───────────────────────────────────────────────
from app.api.orchestration_timeline import router as orchestration_timeline_router
from app.api.decision_engine import router as decision_engine_router
from app.api.control_plane import router as control_plane_router
from app.api.autopilot import router as autopilot_router
from app.api.production import router as production_router
from app.api.brain_memory import router as brain_memory_router

# ── Intelligence / ML ─────────────────────────────────────────────────────
from app.api.ai_engine import router as ai_engine_router
from app.api.rag_chat import router as rag_chat_router
from app.api.ml_recommendation import router as ml_recommendation_router
from app.api.strategy import router as strategy_router

# ── Templates ─────────────────────────────────────────────────────────────
from app.api.templates import router as templates_router
from app.api.template_runtime import router as template_runtime_router
from app.api.template_extraction import router as template_extraction_router
from app.api.template_governance_scheduling import router as template_governance_scheduling_router
from app.api.template_debug import router as template_debug_router

# ── Audio ─────────────────────────────────────────────────────────────────
from app.api.audio import router as audio_router

# ── Avatar / marketplace / commerce (Autovis layer) ───────────────────────
from app.api.avatar_builder import router as avatar_builder_router
from app.api.avatar_commerce import router as avatar_commerce_router
from app.api.product_ingestion import router as product_ingestion_router
from app.api.avatar_marketplace import router as avatar_marketplace_router
from app.api.creator_economy import router as creator_economy_router
from app.api.avatar_localization import router as avatar_localization_router
from app.api.avatar_meta import router as avatar_meta_router
from app.api.avatar_analytics import router as avatar_analytics_router

# ── Creative / channel / publish (Phase 8+) ───────────────────────────────
from app.api.storyboard import router as storyboard_router
from app.api.optimization import router as optimization_router
from app.api.trend_image import router as trend_image_router
from app.api.channel import router as channel_router
from app.api.lookbook import router as lookbook_router
from app.api.motion_clone import router as motion_clone_router
from app.api.patterns import router as patterns_router
from app.api.creative_runs import router as creative_runs_router
from app.api.publish_signal import router as publish_signal_router
from app.api.publish_webhooks import router as publish_webhooks_router

# ── Phase 10-12: Commerce / Avatar / Storyboard / Publish extensions ──────
from app.api.experiment_variants import router as experiment_variants_router
from app.api.experiment_variants import outcome_router as experiment_outcome_router
from app.api.product_learning import router as product_learning_router
from app.api.avatar_embedding import router as avatar_embedding_router
from app.api.render_quality import router as render_quality_router
from app.api.render_quality import router_plural as render_quality_plural_router
from app.api.storyboard_extended import router as storyboard_extended_router
from app.api.publish_compliance import router as publish_compliance_router

_CORE_ROUTERS = [
    health_router,
    storage_router,
    google_accounts_router,
    observability_router,
]

_SCRIPT_ROUTERS = [
    script_upload_preview_router,
    script_validation_router,
    script_regeneration_router,
    provider_payload_preview_router,
    topic_intake_router,
]

_PROJECT_ROUTERS = [
    project_from_preview_router,
    project_workspace_router,
    veo_workspace_router,
]

_RENDER_ROUTERS = [
    render_execution_router,
    render_job_status_router,
    render_dashboard_router,
    render_job_health_router,
    render_events_router,
    provider_callbacks_router,
]

_ORCHESTRATION_ROUTERS = [
    orchestration_timeline_router,
    decision_engine_router,
    control_plane_router,
    autopilot_router,
    production_router,
    brain_memory_router,
]

_INTELLIGENCE_ROUTERS = [
    ai_engine_router,
    rag_chat_router,
    ml_recommendation_router,
    strategy_router,
]

_TEMPLATE_ROUTERS = [
    templates_router,
    template_runtime_router,
    template_extraction_router,
    template_governance_scheduling_router,
    template_debug_router,
]

_AUDIO_ROUTERS = [
    audio_router,
]

_AVATAR_ROUTERS = [
    avatar_builder_router,
    avatar_commerce_router,
    product_ingestion_router,
    avatar_marketplace_router,
    creator_economy_router,
    avatar_localization_router,
    avatar_meta_router,
    avatar_analytics_router,
]

_CREATIVE_ROUTERS = [
    storyboard_router,
    optimization_router,
    trend_image_router,
    channel_router,
    lookbook_router,
    motion_clone_router,
    patterns_router,
    creative_runs_router,
    publish_signal_router,
    publish_webhooks_router,
]

_PHASE_10_12_ROUTERS = [
    experiment_variants_router,
    experiment_outcome_router,
    product_learning_router,
    avatar_embedding_router,
    render_quality_router,
    render_quality_plural_router,
    storyboard_extended_router,
    publish_compliance_router,
]


def register_all_routers(app: FastAPI) -> None:
    """Register every domain router with the FastAPI application."""
    for group in (
        _CORE_ROUTERS,
        _SCRIPT_ROUTERS,
        _PROJECT_ROUTERS,
        _RENDER_ROUTERS,
        _ORCHESTRATION_ROUTERS,
        _INTELLIGENCE_ROUTERS,
        _TEMPLATE_ROUTERS,
        _AUDIO_ROUTERS,
        _AVATAR_ROUTERS,
        _CREATIVE_ROUTERS,
        _PHASE_10_12_ROUTERS,
    ):
        for router in group:
            app.include_router(router)
