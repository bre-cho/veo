"""Tests for the FINAL PRODUCTION LOCK PATCH.

Covers:
1. quick verify completes in < 10 seconds
2. RuntimeRebuildPreflightValidator failure blocks executor (rebuild_fn not called)
3. Production missing PUBLIC_BASE_URL raises clearly (light_runtime_config)
4. Production missing API base URL guard in config.py (public_base_url localhost)
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.render.execution.approved_rebuild_executor import (
    ApprovedRebuildExecutor,
    RuntimeRebuildPreflightValidator,
    _InMemoryIdempotency,
    STATUS_BLOCKED,
    STATUS_SUCCEEDED,
    clear_default_audit_log,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_decision(**overrides) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "project_id": "proj1",
        "episode_id": "ep1",
        "changed_scene_id": "s1",
        "change_type": "subtitle",
        "decision": "allow",
        "rebuild_scene_ids": ["s1", "s2"],
        "selected_strategy": "changed_only",
        "budget_policy": "balanced",
    }
    base.update(overrides)
    return base


def _make_executor(rebuild_fn=None, runtime_preflight=None):
    idempotency = _InMemoryIdempotency()
    executor = ApprovedRebuildExecutor(
        rebuild_fn=rebuild_fn or (lambda p: {"status": "ok", "scenes": p["rebuild_scene_ids"]}),
        idempotency_backend=idempotency,
        runtime_preflight=runtime_preflight,
    )
    return executor


# ---------------------------------------------------------------------------
# 1. Quick verify completes in < 10 seconds
# ---------------------------------------------------------------------------

def test_quick_verify_completes_under_10_seconds():
    """verify_unified_runtime.py --mode quick must complete in under 10 s.

    This guards against re-introducing heavy imports (pydantic/sqlalchemy/etc.)
    into the quick-mode import list.
    """
    import subprocess

    backend_root = Path(__file__).parent.parent
    script = backend_root / "scripts" / "verify_unified_runtime.py"

    start = time.monotonic()
    result = subprocess.run(
        [sys.executable, str(script), "--mode", "quick"],
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ, "PYTHONPATH": str(backend_root)},
    )
    elapsed = time.monotonic() - start

    assert elapsed < 10, (
        f"Quick verify took {elapsed:.1f}s (> 10s). "
        f"A heavy import may have been added to _QUICK_IMPORTS.\n"
        f"stdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}"
    )


# ---------------------------------------------------------------------------
# 2. RuntimeRebuildPreflightValidator failure blocks executor
# ---------------------------------------------------------------------------

class _AlwaysFailRuntimePreflight:
    """Stub RuntimeRebuildPreflightValidator that always fails."""

    def validate(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        return {"valid": False, "reason": "stub runtime check: project does not exist", "warnings": []}


def test_runtime_preflight_failure_blocks_executor_and_skips_rebuild():
    """When runtime preflight fails, executor returns STATUS_BLOCKED and rebuild_fn is NOT called."""
    clear_default_audit_log()
    rebuild_calls: List[Any] = []

    executor = _make_executor(
        rebuild_fn=lambda p: (rebuild_calls.append(p), {"status": "ok"})[1],
        runtime_preflight=_AlwaysFailRuntimePreflight(),
    )

    result = executor.execute(_make_decision())

    assert result["status"] == STATUS_BLOCKED, f"Expected blocked, got {result['status']}"
    assert len(rebuild_calls) == 0, "rebuild_fn must not be called when runtime preflight fails"
    assert "runtime preflight" in result.get("message", "").lower(), (
        f"Expected 'runtime preflight' in message, got: {result.get('message')}"
    )


def test_runtime_preflight_success_allows_executor():
    """When runtime preflight passes, executor proceeds normally to STATUS_SUCCEEDED."""
    clear_default_audit_log()

    class _AlwaysPassRuntimePreflight:
        def validate(self, decision):
            return {"valid": True, "reason": "", "warnings": []}

    rebuild_calls: List[Any] = []

    executor = _make_executor(
        rebuild_fn=lambda p: (rebuild_calls.append(p), {"status": "ok"})[1],
        runtime_preflight=_AlwaysPassRuntimePreflight(),
    )

    result = executor.execute(_make_decision())

    assert result["status"] == STATUS_SUCCEEDED
    assert len(rebuild_calls) == 1


def test_no_runtime_preflight_does_not_block():
    """When runtime_preflight is None (default), execution proceeds without runtime checks."""
    clear_default_audit_log()

    executor = _make_executor(runtime_preflight=None)
    result = executor.execute(_make_decision())

    assert result["status"] == STATUS_SUCCEEDED


# ---------------------------------------------------------------------------
# 3. Production missing PUBLIC_BASE_URL raises in light_runtime_config
# ---------------------------------------------------------------------------

def test_light_runtime_config_raises_on_localhost_in_production():
    """light_runtime_config must raise ValueError if PUBLIC_BASE_URL is localhost in production."""
    import importlib
    import types

    # We simulate a production env with a localhost URL by patching os.environ
    env_patch = {
        "APP_ENV": "production",
        "PUBLIC_BASE_URL": "http://localhost:8000",
    }

    # Remove cached module so it re-evaluates module-level code
    mod_name = "app.core.light_runtime_config"
    original = sys.modules.pop(mod_name, None)
    try:
        with patch.dict(os.environ, env_patch, clear=False):
            try:
                importlib.import_module(mod_name)
                raise AssertionError("Expected ValueError was not raised")
            except ValueError as exc:
                assert "localhost" in str(exc).lower() or "PUBLIC_BASE_URL" in str(exc)
    finally:
        # Restore previous module state
        sys.modules.pop(mod_name, None)
        if original is not None:
            sys.modules[mod_name] = original


def test_light_runtime_config_no_error_in_development():
    """light_runtime_config must not raise when APP_ENV=development even with localhost URL."""
    import importlib

    mod_name = "app.core.light_runtime_config"
    original = sys.modules.pop(mod_name, None)
    try:
        env_patch = {
            "APP_ENV": "development",
            "PUBLIC_BASE_URL": "http://localhost:8000",
        }
        with patch.dict(os.environ, env_patch, clear=False):
            # Should not raise
            mod = importlib.import_module(mod_name)
            assert mod.app_env == "development"
    finally:
        sys.modules.pop(mod_name, None)
        if original is not None:
            sys.modules[mod_name] = original


# ---------------------------------------------------------------------------
# 4. config.py raises on localhost in production
# ---------------------------------------------------------------------------

def test_config_raises_on_localhost_public_base_url_in_production():
    """app.core.config must raise ValueError if PUBLIC_BASE_URL=localhost and APP_ENV=production."""
    import importlib

    mod_name = "app.core.config"
    original = sys.modules.pop(mod_name, None)
    try:
        env_patch = {
            "APP_ENV": "production",
            "PUBLIC_BASE_URL": "http://localhost:8000",
            "PROVIDER_ALLOW_MOCK_FALLBACK": "false",
        }
        with patch.dict(os.environ, env_patch, clear=False):
            try:
                importlib.import_module(mod_name)
                raise AssertionError("Expected ValueError was not raised")
            except ValueError as exc:
                assert "localhost" in str(exc).lower() or "PUBLIC_BASE_URL" in str(exc)
    finally:
        sys.modules.pop(mod_name, None)
        if original is not None:
            sys.modules[mod_name] = original
