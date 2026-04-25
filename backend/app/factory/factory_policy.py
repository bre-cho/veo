"""factory_policy – policy guards that control whether a job must go through
the Factory pipeline and how it behaves in each mode.

Policy modes
------------
production  : all video jobs MUST be dispatched via FactoryRun; direct calls
              to individual services are blocked unless called from within a
              stage adapter.
staging     : factory pipeline is enforced but some gates are advisory only.
dev         : factory pipeline is optional; direct service calls are allowed.
"""
from __future__ import annotations

import os


def get_policy_mode() -> str:
    """Read the active policy mode from the environment."""
    return os.getenv("FACTORY_POLICY_MODE", os.getenv("APP_ENV", "dev")).lower()


def require_factory_run(policy_mode: str | None = None) -> bool:
    """Return True if the current policy requires all jobs to use a FactoryRun."""
    mode = (policy_mode or get_policy_mode()).lower()
    return mode in ("production", "staging")


def max_stage_retries(policy_mode: str | None = None) -> int:
    """Return the maximum number of automatic retries per stage."""
    mode = (policy_mode or get_policy_mode()).lower()
    return {"production": 3, "staging": 2, "dev": 1}.get(mode, 1)


def gate_is_blocking(gate_name: str, policy_mode: str | None = None) -> bool:
    """Return True if a failed gate should block the run (not just warn)."""
    mode = (policy_mode or get_policy_mode()).lower()
    if mode == "dev":
        return False  # advisory only in dev
    blocking_gates = {
        "script_gate",
        "scene_gate",
        "avatar_gate",
        "audio_gate",
        "render_gate",
        "subtitle_gate",
        "seo_gate",
        "publish_gate",
        "analytics_gate",
    }
    return gate_name in blocking_gates
