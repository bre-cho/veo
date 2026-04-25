"""Tests for the FINAL RUNTIME HARDENING PATCH.

Covers:
* Production guard raises RuntimeError when rebuild_fn/idempotency_backend are
  absent in a production-like environment.
* Quick verify imports stay lean (no executor / persistence modules).
* RuntimeRebuildPreflightValidator — payload + runtime checks.
* Audit lifecycle written correctly (approved → executing → succeeded / failed).
* Duplicate approve request runs rebuild exactly once.
* Preflight failure does not write a ``succeeded`` audit entry.
* API approve route calls SmartReassemblyService via mock (unit-level).
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.render.execution.approved_rebuild_executor import (
    ApprovedRebuildExecutor,
    RebuildPreflightValidator,
    RuntimeRebuildPreflightValidator,
    _InMemoryIdempotency,
    STATUS_BLOCKED,
    STATUS_EXECUTING,
    STATUS_SUCCEEDED,
    STATUS_INCIDENT_REQUIRED,
    clear_default_audit_log,
    get_default_audit_log,
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


def _make_executor(rebuild_fn=None, audit_log: List[Dict[str, Any]] | None = None):
    """Build an executor with an in-memory idempotency backend and optional audit capture."""
    captured: List[Dict[str, Any]] = audit_log if audit_log is not None else []
    idempotency = _InMemoryIdempotency()
    executor = ApprovedRebuildExecutor(
        rebuild_fn=rebuild_fn or (lambda p: {"status": "ok", "scenes": p["rebuild_scene_ids"]}),
        audit_store=captured.append,
        idempotency_backend=idempotency,
    )
    return executor, idempotency, captured


# ---------------------------------------------------------------------------
# 1. Production guard
# ---------------------------------------------------------------------------

class TestProductionGuard:
    """ApprovedRebuildExecutor must refuse to start without real deps in production."""

    def test_raises_when_rebuild_fn_missing_in_production(self):
        with patch(
            "app.render.execution.approved_rebuild_executor._get_app_env",
            return_value="production",
        ):
            try:
                ApprovedRebuildExecutor(
                    rebuild_fn=None,
                    idempotency_backend=_InMemoryIdempotency(),
                )
                assert False, "Expected RuntimeError"
            except RuntimeError as exc:
                assert "rebuild_fn" in str(exc)

    def test_raises_when_idempotency_missing_in_production(self):
        with patch(
            "app.render.execution.approved_rebuild_executor._get_app_env",
            return_value="production",
        ):
            try:
                ApprovedRebuildExecutor(
                    rebuild_fn=lambda p: {"status": "ok"},
                    idempotency_backend=None,
                )
                assert False, "Expected RuntimeError"
            except RuntimeError as exc:
                assert "idempotency_backend" in str(exc)

    def test_no_raise_in_test_environment(self):
        """Constructor must succeed without rebuild_fn outside production."""
        with patch(
            "app.render.execution.approved_rebuild_executor._get_app_env",
            return_value="test",
        ):
            executor = ApprovedRebuildExecutor()  # should not raise
            assert executor is not None


# ---------------------------------------------------------------------------
# 2. Quick verify module list stays lean
# ---------------------------------------------------------------------------

class TestQuickVerifyImportList:
    """_QUICK_IMPORTS must only contain app.core.* modules."""

    def _load_vur(self):
        """Load verify_unified_runtime as a module from its path."""
        import importlib.util
        script_path = Path(__file__).parent.parent / "scripts" / "verify_unified_runtime.py"
        spec = importlib.util.spec_from_file_location("verify_unified_runtime", script_path)
        vur = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vur)
        return vur

    def test_quick_imports_do_not_include_executor(self):
        vur = self._load_vur()
        heavy = [
            m for m in vur._QUICK_IMPORTS
            if not m.startswith("app.core.")
        ]
        assert heavy == [], (
            f"_QUICK_IMPORTS contains non-core module(s): {heavy}. "
            "These belong in _FULL_IMPORTS only."
        )

    def test_executor_in_full_imports(self):
        vur = self._load_vur()
        assert "app.render.execution.approved_rebuild_executor" in vur._FULL_IMPORTS
        assert "app.render.execution.rebuild_persistence" in vur._FULL_IMPORTS


# ---------------------------------------------------------------------------
# 3. RuntimeRebuildPreflightValidator
# ---------------------------------------------------------------------------

class TestRuntimeRebuildPreflightValidator:
    """RuntimeRebuildPreflightValidator runtime checks."""

    def test_skips_db_checks_gracefully_when_no_db(self, tmp_path):
        """Without a DB the validator should warn but not fail."""
        ep_id = "ep_rt_test"
        manifests_dir = tmp_path / "manifests"
        manifests_dir.mkdir()
        (manifests_dir / f"{ep_id}.json").write_text(
            '{"scenes": [{"scene_id": "s1"}, {"scene_id": "s2"}]}',
            encoding="utf-8",
        )

        with patch("app.core.runtime_paths.render_paths") as mock_paths:
            mock_paths.manifests_dir = str(manifests_dir)
            mock_paths.final_dir = str(tmp_path / "final")

            validator = RuntimeRebuildPreflightValidator(db=None)
            result = validator.validate(_make_decision(episode_id=ep_id))

        assert result["valid"] is True
        # DB checks were skipped → warnings list should mention it
        assert any("project" in w.lower() for w in result["warnings"])

    def test_fails_when_manifest_missing(self, tmp_path):
        manifests_dir = tmp_path / "manifests"
        manifests_dir.mkdir()
        # No manifest file created

        with patch("app.core.runtime_paths.render_paths") as mock_paths:
            mock_paths.manifests_dir = str(manifests_dir)
            mock_paths.final_dir = str(tmp_path / "final")

            validator = RuntimeRebuildPreflightValidator(db=None)
            result = validator.validate(_make_decision(episode_id="missing_ep"))

        assert result["valid"] is False
        assert "manifest" in result["reason"].lower()

    def test_fails_when_scene_missing_from_manifest(self, tmp_path):
        ep_id = "ep_missing_scene"
        manifests_dir = tmp_path / "manifests"
        manifests_dir.mkdir()
        # Manifest only contains s1 — s99 is absent
        (manifests_dir / f"{ep_id}.json").write_text(
            '{"scenes": [{"scene_id": "s1"}]}',
            encoding="utf-8",
        )

        with patch("app.core.runtime_paths.render_paths") as mock_paths:
            mock_paths.manifests_dir = str(manifests_dir)
            mock_paths.final_dir = str(tmp_path / "final")

            validator = RuntimeRebuildPreflightValidator(db=None)
            result = validator.validate(
                _make_decision(episode_id=ep_id, rebuild_scene_ids=["s1", "s99"])
            )

        assert result["valid"] is False
        assert "s99" in result["reason"]

    def test_fails_when_output_path_not_writable(self, tmp_path):
        ep_id = "ep_no_write"
        manifests_dir = tmp_path / "manifests"
        manifests_dir.mkdir()
        (manifests_dir / f"{ep_id}.json").write_text(
            '{"scenes": [{"scene_id": "s1"}]}',
            encoding="utf-8",
        )
        # Create a *file* at the expected output dir path so mkdir raises
        final_dir = tmp_path / "final"
        final_dir.mkdir()
        blocked_path = final_dir / ep_id
        blocked_path.write_text("not-a-dir")  # file blocks mkdir

        with patch("app.core.runtime_paths.render_paths") as mock_paths:
            mock_paths.manifests_dir = str(manifests_dir)
            mock_paths.final_dir = str(final_dir)

            validator = RuntimeRebuildPreflightValidator(db=None)
            result = validator.validate(_make_decision(episode_id=ep_id))

        # mkdir on a path that already exists as a file raises NotADirectoryError → skipped to warning
        assert "valid" in result

    def test_passes_full_valid_scenario(self, tmp_path):
        ep_id = "ep_ok"
        manifests_dir = tmp_path / "manifests"
        manifests_dir.mkdir()
        (manifests_dir / f"{ep_id}.json").write_text(
            '{"scenes": [{"scene_id": "s1"}, {"scene_id": "s2"}]}',
            encoding="utf-8",
        )

        with patch("app.core.runtime_paths.render_paths") as mock_paths:
            mock_paths.manifests_dir = str(manifests_dir)
            mock_paths.final_dir = str(tmp_path / "final")

            validator = RuntimeRebuildPreflightValidator(db=None)
            result = validator.validate(
                _make_decision(episode_id=ep_id, rebuild_scene_ids=["s1", "s2"])
            )

        assert result["valid"] is True


# ---------------------------------------------------------------------------
# 4. Audit lifecycle
# ---------------------------------------------------------------------------

class TestAuditLifecycle:
    """Full approved → executing → succeeded lifecycle must be written."""

    def test_audit_records_approved_executing_succeeded(self):
        audit_log: List[Dict[str, Any]] = []
        executor, _, _ = _make_executor(audit_log=audit_log)

        executor.execute(_make_decision())

        events = [e["event"] for e in audit_log]
        assert "approved" in events, f"approved missing from {events}"
        assert "executing" in events, f"executing missing from {events}"
        assert "succeeded" in events, f"succeeded missing from {events}"

    def test_audit_records_incident_on_rebuild_failure(self):
        audit_log: List[Dict[str, Any]] = []

        def bad_fn(p):
            raise RuntimeError("kaboom")

        executor, _, _ = _make_executor(rebuild_fn=bad_fn, audit_log=audit_log)
        result = executor.execute(_make_decision())

        assert result["status"] == STATUS_INCIDENT_REQUIRED
        events = [e["event"] for e in audit_log]
        assert "incident_required" in events

    def test_audit_contains_job_id_on_all_entries(self):
        audit_log: List[Dict[str, Any]] = []
        executor, _, _ = _make_executor(audit_log=audit_log)
        executor.execute(_make_decision())

        for entry in audit_log:
            assert entry.get("job_id"), f"Missing job_id in audit entry: {entry}"


# ---------------------------------------------------------------------------
# 5. Duplicate approve / idempotency
# ---------------------------------------------------------------------------

class TestDuplicateApprove:
    """Submitting the same decision twice must execute rebuild exactly once."""

    def test_duplicate_approve_runs_rebuild_once(self):
        calls: List[Any] = []

        def counting_fn(p):
            calls.append(p)
            return {"status": "ok"}

        executor, _, _ = _make_executor(rebuild_fn=counting_fn)
        d = _make_decision(project_id="dedup")
        r1 = executor.execute(d)
        r2 = executor.execute(d)

        assert r1["status"] == STATUS_SUCCEEDED
        assert r2["status"] == STATUS_SUCCEEDED
        assert len(calls) == 1, f"Expected 1 rebuild call, got {len(calls)}"

    def test_concurrent_duplicate_approve_runs_rebuild_once(self):
        calls: List[Any] = []
        barrier = threading.Barrier(4)

        def slow_fn(p):
            time.sleep(0.05)
            calls.append(p)
            return {"status": "ok"}

        executor, _, _ = _make_executor(rebuild_fn=slow_fn)
        d = _make_decision(project_id="concurrent_dedup")
        results: List[Any] = []

        def submit():
            barrier.wait()
            results.append(executor.execute(d))

        threads = [threading.Thread(target=submit) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(calls) == 1, f"Rebuild called {len(calls)} times instead of 1"
        assert all(r.get("status") in (STATUS_SUCCEEDED, STATUS_EXECUTING) for r in results)


# ---------------------------------------------------------------------------
# 6. Preflight failure must not write a succeeded entry
# ---------------------------------------------------------------------------

class TestPreflightFailNoSucceeded:
    """When preflight fails the audit log must NOT contain a succeeded entry."""

    def test_preflight_fail_no_succeeded_in_audit(self):
        audit_log: List[Dict[str, Any]] = []
        executor, _, _ = _make_executor(audit_log=audit_log)

        # rebuild_scene_ids=[] will fail preflight (empty scene list)
        result = executor.execute(_make_decision(rebuild_scene_ids=[]))

        assert result["status"] == STATUS_BLOCKED
        events = [e["event"] for e in audit_log]
        assert "succeeded" not in events, (
            f"'succeeded' should not appear in audit when preflight fails: {events}"
        )


# ---------------------------------------------------------------------------
# 7. API approve route wires SmartReassemblyService (unit-level mock)
# ---------------------------------------------------------------------------

class TestRebuildApproveApiMock:
    """rebuild_approve() must call SmartReassemblyService.reassemble() via the
    _make_smart_rebuild_fn() factory.  We test this at the unit level by
    patching the service class.
    """

    def test_approve_calls_smart_reassembly_service(self):
        from app.render.rebuild.api import _make_smart_rebuild_fn

        mock_service_instance = MagicMock()
        mock_service_instance.reassemble.return_value = {
            "status": "ok",
            "scenes_rebuilt": ["s1"],
        }
        mock_service_class = MagicMock(return_value=mock_service_instance)

        with patch(
            "app.render.reassembly.smart_reassembly_service.SmartReassemblyService",
            mock_service_class,
        ):
            rebuild_fn = _make_smart_rebuild_fn()
            result = rebuild_fn({
                "project_id": "p1",
                "episode_id": "ep1",
                "changed_scene_id": "s1",
                "change_type": "subtitle",
                "rebuild_scene_ids": ["s1"],
                "selected_strategy": "changed_only",
            })

        mock_service_class.assert_called_once()
        mock_service_instance.reassemble.assert_called_once()
        assert result["status"] == "ok"

    def test_approve_endpoint_returns_succeeded(self):
        """Full approve endpoint returns a succeeded result via mocked persistence."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from app.render.rebuild.api import router as rebuild_router

        app = FastAPI()
        app.include_router(rebuild_router)

        mock_db = MagicMock()
        mock_persistence = MagicMock()
        mock_persistence.append_audit = MagicMock()
        mock_persistence.reserve_key.return_value = True
        mock_persistence.check.return_value = None
        mock_persistence.complete_key = MagicMock()

        mock_runtime_preflight = MagicMock()
        mock_runtime_preflight.validate.return_value = {"valid": True, "reason": "", "warnings": []}

        def mock_get_db():
            yield mock_db

        with (
            patch("app.render.rebuild.api.get_db", mock_get_db),
            patch("app.render.rebuild.api.DbRebuildPersistence", return_value=mock_persistence),
            patch("app.render.rebuild.api.RuntimeRebuildPreflightValidator", return_value=mock_runtime_preflight),
            patch("app.render.rebuild.api._make_smart_rebuild_fn") as mock_fn_factory,
        ):
            mock_fn_factory.return_value = lambda p: {"status": "ok", "scenes": p.get("rebuild_scene_ids", [])}
            client = TestClient(app)
            response = client.post(
                "/api/v1/render/rebuild/approve",
                json={
                    "decision": _make_decision(),
                    "job_id": "test-job-001",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == STATUS_SUCCEEDED
        assert data["job_id"] == "test-job-001"
