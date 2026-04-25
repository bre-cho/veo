"""Router registry – groups all API routers by domain.

Import ``register_all_routers`` and call it with the FastAPI app instance
instead of listing every router in ``main.py``.  This keeps ``main.py`` thin
and avoids merge conflicts when new routers are added.

Routers are imported lazily inside ``register_all_routers()`` so that a single
broken dependency cannot prevent the whole API process from starting.  Failed
imports are logged as warnings and that router is silently skipped.
"""
from __future__ import annotations

import importlib
import logging

from fastapi import FastAPI

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Router specification lists
# Each entry: (module_path, attribute_name)
# The attribute may be a single APIRouter **or** a list[APIRouter].
# ---------------------------------------------------------------------------

# Routers that are expected to be available in every environment.
_REQUIRED_ROUTER_SPECS: list[tuple[str, str]] = [
    # Core / infrastructure
    ("app.api.health", "router"),
    ("app.api.storage", "router"),
    ("app.api.google_accounts", "router"),
    ("app.api.observability", "router"),
    # Script / preview pipeline
    ("app.api.script_upload_preview", "router"),
    ("app.api.script_validation", "router"),
    ("app.api.script_regeneration_routes", "router"),
    ("app.api.provider_payload_preview", "router"),
    ("app.api.topic_intake", "router"),
    # Project workspace
    ("app.api.project_from_preview", "router"),
    ("app.api.project_workspace", "router"),
    ("app.api.veo_workspace", "router"),
    # Render execution
    ("app.api.render_execution", "router"),
    ("app.api.render_job_status", "router"),
    ("app.api.render_dashboard", "router"),
    ("app.api.render_job_health", "router"),
    ("app.api.render_events", "router"),
    ("app.api.provider_callbacks", "router"),
    # Orchestration / control
    ("app.api.orchestration_timeline", "router"),
    ("app.api.decision_engine", "router"),
    ("app.api.control_plane", "router"),
    ("app.api.autopilot", "router"),
    ("app.api.autopilot_brain", "router"),
    ("app.api.production", "router"),
    ("app.api.brain_memory", "router"),
    # Intelligence / ML
    ("app.api.ai_engine", "router"),
    ("app.api.rag_chat", "router"),
    ("app.api.ml_recommendation", "router"),
    ("app.api.strategy", "router"),
    # Templates
    ("app.api.templates", "router"),
    ("app.api.template_runtime", "router"),
    ("app.api.template_extraction", "router"),
    ("app.api.template_governance_scheduling", "router"),
    ("app.api.template_debug", "router"),
    ("app.api.avatar_debug", "router"),
    # Audio
    ("app.api.audio", "router"),
    # Avatar / marketplace / commerce
    ("app.api.avatar_builder", "router"),
    ("app.api.avatar_commerce", "router"),
    ("app.api.product_ingestion", "router"),
    ("app.api.avatar_marketplace", "router"),
    ("app.api.creator_economy", "router"),
    ("app.api.avatar_localization", "router"),
    ("app.api.avatar_meta", "router"),
    ("app.api.avatar_analytics", "router"),
    # Creative / channel / publish
    ("app.api.storyboard", "router"),
    ("app.api.optimization", "router"),
    ("app.api.trend_image", "router"),
    ("app.api.channel", "router"),
    ("app.api.lookbook", "router"),
    ("app.api.motion_clone", "router"),
    ("app.api.patterns", "router"),
    ("app.api.creative_runs", "router"),
    ("app.api.publish_signal", "router"),
    ("app.api.publish_webhooks", "router"),
    # Phase 10-12 extensions
    ("app.api.experiment_variants", "router"),
    ("app.api.experiment_variants", "outcome_router"),
    ("app.api.product_learning", "router"),
    ("app.api.avatar_embedding", "router"),
    ("app.api.render_quality", "router"),
    ("app.api.render_quality", "router_plural"),
    ("app.api.storyboard_extended", "router"),
    ("app.api.publish_compliance", "router"),
]

# Routers with optional / infrastructure dependencies — failures are expected
# in lean environments and are always logged as warnings, never errors.
_OPTIONAL_ROUTER_SPECS: list[tuple[str, str]] = [
    ("app.api.avatar_tournament", "router"),
    ("app.api.avatar_governance", "router"),
    ("app.api.avatar_acting", "router"),
    # Drama engine (returns a list of routers)
    ("app.drama.api", "ALL_DRAMA_ROUTERS"),
    # Render sub-domain routers
    ("app.render.assembly.api", "router"),
    ("app.render.manifest.api", "router"),
    ("app.render.rerender.api", "router"),
    ("app.render.reassembly.api", "router"),
    ("app.render.dependency.api", "router"),
    ("app.render.rebuild.api", "router"),
]


def _import_router(module_path: str, attr: str, *, optional: bool) -> list:
    """Import *attr* from *module_path* and return a flat list of routers.

    Returns an empty list on failure (always for optional specs; logged as
    a warning for required specs so operators can investigate).
    """
    try:
        mod = importlib.import_module(module_path)
        obj = getattr(mod, attr)
        if isinstance(obj, list):
            return [r for r in obj if r is not None]
        if obj is not None:
            return [obj]
        return []
    except Exception as exc:  # noqa: BLE001
        level = _log.warning if optional else _log.error
        level("Router %s.%s failed to import: %s", module_path, attr, exc)
        return []


def register_all_routers(app: FastAPI) -> None:
    """Lazily import and register every domain router with *app*."""
    for module_path, attr in _REQUIRED_ROUTER_SPECS:
        for router in _import_router(module_path, attr, optional=False):
            app.include_router(router)

    for module_path, attr in _OPTIONAL_ROUTER_SPECS:
        for router in _import_router(module_path, attr, optional=True):
            app.include_router(router)

