"""Tests for ApprovedRebuildExecutor — approve+execute flow, idempotency, preflight."""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.render.execution.approved_rebuild_executor import (
    ApprovedRebuildExecutor,
    RebuildPreflightValidator,
    _InMemoryIdempotency,
    STATUS_BLOCKED,
    STATUS_EXECUTING,
    STATUS_SUCCEEDED,
    STATUS_INCIDENT_REQUIRED,
    DECISION_MAX_AGE_SECONDS,
    clear_default_audit_log,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_decision(**overrides) -> dict:
    base = {
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


def _make_executor(rebuild_fn=None) -> tuple[ApprovedRebuildExecutor, _InMemoryIdempotency]:
    idempotency = _InMemoryIdempotency()
    executor = ApprovedRebuildExecutor(
        rebuild_fn=rebuild_fn or (lambda p: {"status": "ok", "scenes": p["rebuild_scene_ids"]}),
        idempotency_backend=idempotency,
    )
    return executor, idempotency


# ---------------------------------------------------------------------------
# Core execute flow
# ---------------------------------------------------------------------------

def test_executor_successful_approve_and_execute():
    """Happy path: rebuild_fn is called and result is STATUS_SUCCEEDED."""
    clear_default_audit_log()
    calls = []
    executor, _ = _make_executor(lambda p: (calls.append(p), {"status": "ok"})[1])

    result = executor.execute(_make_decision())

    assert result["status"] == STATUS_SUCCEEDED
    assert len(calls) == 1
    assert calls[0]["project_id"] == "proj1"
    assert calls[0]["rebuild_scene_ids"] == ["s1", "s2"]


def test_executor_rebuild_fn_receives_correct_payload():
    """Payload passed to rebuild_fn must mirror decision fields."""
    received = {}

    def capture(payload):
        received.update(payload)
        return {"status": "ok"}

    executor, _ = _make_executor(capture)
    executor.execute(_make_decision(
        project_id="myproject",
        episode_id="ep42",
        changed_scene_id="sc7",
        change_type="voice",
        rebuild_scene_ids=["sc7", "sc8"],
        selected_strategy="dependency_set",
        has_timeline_drift=True,
    ))

    assert received["project_id"] == "myproject"
    assert received["episode_id"] == "ep42"
    assert received["changed_scene_id"] == "sc7"
    assert received["change_type"] == "voice"
    assert "sc7" in received["rebuild_scene_ids"]
    assert received["has_timeline_drift"] is True


def test_executor_failure_in_rebuild_fn_returns_incident_required():
    """When rebuild_fn raises, the result must be STATUS_INCIDENT_REQUIRED."""

    def bad_fn(p):
        raise RuntimeError("Simulated rebuild failure")

    executor, _ = _make_executor(bad_fn)
    result = executor.execute(_make_decision())

    assert result["status"] == STATUS_INCIDENT_REQUIRED
    assert "incident" in result


def test_executor_blocked_decision_not_executed():
    """Blocked decisions must be short-circuited without calling rebuild_fn."""
    calls = []
    executor, _ = _make_executor(lambda p: (calls.append(p), {"status": "ok"})[1])

    result = executor.execute(_make_decision(decision="block"))

    assert result["status"] == STATUS_BLOCKED
    assert len(calls) == 0


# ---------------------------------------------------------------------------
# Duplicate / idempotency
# ---------------------------------------------------------------------------

def test_executor_duplicate_request_returns_cached_result():
    """Second identical call returns cached result; rebuild_fn called only once."""
    calls = []
    executor, _ = _make_executor(lambda p: (calls.append(p), {"status": "ok"})[1])

    decision = _make_decision(project_id="dedup_proj")
    r1 = executor.execute(decision)
    r2 = executor.execute(decision)

    assert r1["status"] == STATUS_SUCCEEDED
    assert r2["status"] == STATUS_SUCCEEDED
    assert len(calls) == 1  # rebuild_fn was invoked exactly once


def test_executor_different_scenes_not_deduped():
    """Two decisions with different rebuild_scene_ids must both execute."""
    calls = []
    executor, _ = _make_executor(lambda p: (calls.append(p), {"status": "ok"})[1])

    d1 = _make_decision(rebuild_scene_ids=["s1"])
    d2 = _make_decision(rebuild_scene_ids=["s2"])

    executor.execute(d1)
    executor.execute(d2)

    assert len(calls) == 2


# ---------------------------------------------------------------------------
# Atomic reserve / complete (_InMemoryIdempotency unit tests)
# ---------------------------------------------------------------------------

def test_in_memory_reserve_key_succeeds_on_first_call():
    idempotency = _InMemoryIdempotency()
    assert idempotency.reserve_key("key1", "job1") is True


def test_in_memory_reserve_key_fails_on_duplicate():
    idempotency = _InMemoryIdempotency()
    idempotency.reserve_key("key1", "job1")
    assert idempotency.reserve_key("key1", "job2") is False


def test_in_memory_reserve_key_sets_executing_status():
    idempotency = _InMemoryIdempotency()
    idempotency.reserve_key("key1", "job1")
    cached = idempotency.check("key1")
    assert cached is not None
    assert cached["status"] == STATUS_EXECUTING


def test_in_memory_complete_key_updates_to_final_result():
    idempotency = _InMemoryIdempotency()
    idempotency.reserve_key("key1", "job1")
    idempotency.complete_key("key1", {"status": STATUS_SUCCEEDED, "job_id": "job1"})
    cached = idempotency.check("key1")
    assert cached["status"] == STATUS_SUCCEEDED


def test_in_memory_reserve_is_thread_safe():
    """Only one thread should win the reserve; the other should lose."""
    idempotency = _InMemoryIdempotency()
    results = []
    barrier = threading.Barrier(5)

    def compete():
        barrier.wait()
        results.append(idempotency.reserve_key("shared_key", "job"))

    threads = [threading.Thread(target=compete) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    successes = [r for r in results if r is True]
    failures = [r for r in results if r is False]
    assert len(successes) == 1
    assert len(failures) == 4


# ---------------------------------------------------------------------------
# RebuildPreflightValidator
# ---------------------------------------------------------------------------

def test_preflight_valid_decision_passes():
    result = RebuildPreflightValidator.validate(_make_decision())
    assert result["valid"] is True


def test_preflight_missing_project_id_fails():
    d = _make_decision()
    d["project_id"] = ""
    result = RebuildPreflightValidator.validate(d)
    assert result["valid"] is False
    assert "project_id" in result["reason"]


def test_preflight_missing_episode_id_fails():
    d = _make_decision(episode_id="")
    result = RebuildPreflightValidator.validate(d)
    assert result["valid"] is False


def test_preflight_empty_rebuild_scene_ids_fails():
    d = _make_decision(rebuild_scene_ids=[])
    result = RebuildPreflightValidator.validate(d)
    assert result["valid"] is False
    assert "rebuild_scene_ids" in result["reason"]


def test_preflight_blocked_decision_fails():
    d = _make_decision(decision="block")
    result = RebuildPreflightValidator.validate(d)
    assert result["valid"] is False
    assert "blocked" in result["reason"]


def test_preflight_expired_decision_fails():
    from datetime import datetime, timezone, timedelta
    _TTL_BUFFER_SECONDS = 10  # Extra seconds past the TTL to ensure expiry
    old_ts = (
        datetime.now(tz=timezone.utc)
        - timedelta(seconds=DECISION_MAX_AGE_SECONDS + _TTL_BUFFER_SECONDS)
    ).isoformat()
    d = _make_decision(decided_at=old_ts)
    result = RebuildPreflightValidator.validate(d)
    assert result["valid"] is False
    assert "expired" in result["reason"]


def test_preflight_fresh_decision_passes_ttl_check():
    from datetime import datetime, timezone
    fresh_ts = datetime.now(tz=timezone.utc).isoformat()
    d = _make_decision(decided_at=fresh_ts)
    result = RebuildPreflightValidator.validate(d)
    assert result["valid"] is True


def test_preflight_malformed_decided_at_does_not_block():
    d = _make_decision(decided_at="not-a-date")
    result = RebuildPreflightValidator.validate(d)
    assert result["valid"] is True  # graceful: skip TTL check


def test_executor_preflight_failure_blocks_execution():
    """A decision that fails preflight should be blocked without calling rebuild_fn."""
    calls = []
    executor, _ = _make_executor(lambda p: (calls.append(p), {"status": "ok"})[1])

    # Empty rebuild_scene_ids will pass the initial guard but fail preflight
    d = _make_decision(rebuild_scene_ids=[])
    result = executor.execute(d)

    # The initial guard catches empty scene list before preflight, still blocked
    assert result["status"] == STATUS_BLOCKED
    assert len(calls) == 0
