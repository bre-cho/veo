"""Tests for LLM function calling (function_registry + function_executor)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.render_job import RenderJob
from app.models.render_scene_task import RenderSceneTask
from app.models.render_incident_state import RenderIncidentState
from app.models.render_timeline_event import RenderTimelineEvent
from app.services.llm.function_registry import ALLOWED_TOOL_NAMES, TOOL_REGISTRY
from app.services.llm.function_executor import execute_tool


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _add_job(db, job_id: str = "job-fn-1", status: str = "queued") -> RenderJob:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    j = RenderJob(
        id=job_id,
        project_id="proj-fn",
        provider="veo",
        status=status,
        planned_scene_count=2,
        completed_scene_count=0,
        failed_scene_count=0,
        created_at=now,
    )
    db.add(j)
    db.commit()
    return j


# ── Registry ──────────────────────────────────────────────────────────────────


def test_tool_registry_is_non_empty():
    assert len(TOOL_REGISTRY) > 0


def test_all_tool_names_in_whitelist():
    for tool in TOOL_REGISTRY:
        assert tool["function"]["name"] in ALLOWED_TOOL_NAMES


def test_tools_have_required_fields():
    for tool in TOOL_REGISTRY:
        assert tool["type"] == "function"
        fn = tool["function"]
        assert "name" in fn
        assert "description" in fn
        assert "parameters" in fn


# ── Executor – whitelist enforcement ─────────────────────────────────────────


def test_reject_unknown_tool():
    db = _session()
    result = execute_tool(db, tool_name="drop_database", tool_args={})
    assert "error" in result
    assert "not permitted" in result["error"].lower()


def test_reject_injected_tool():
    db = _session()
    result = execute_tool(db, tool_name="os_exec", tool_args={"cmd": "rm -rf /"})
    assert "error" in result


# ── get_job_status ────────────────────────────────────────────────────────────


def test_get_job_status_found():
    db = _session()
    _add_job(db, job_id="job-status-1", status="queued")
    result = execute_tool(db, tool_name="get_job_status", tool_args={"job_id": "job-status-1"})
    assert result["job_id"] == "job-status-1"
    assert result["status"] == "queued"
    assert "planned_scene_count" in result


def test_get_job_status_not_found():
    db = _session()
    result = execute_tool(db, tool_name="get_job_status", tool_args={"job_id": "nonexistent"})
    assert "error" in result


def test_get_job_status_missing_arg():
    db = _session()
    result = execute_tool(db, tool_name="get_job_status", tool_args={})
    assert "error" in result


# ── list_recent_jobs ──────────────────────────────────────────────────────────


def test_list_recent_jobs_default():
    db = _session()
    for i in range(3):
        _add_job(db, job_id=f"job-list-{i}", status="queued")
    result = execute_tool(db, tool_name="list_recent_jobs", tool_args={})
    assert "jobs" in result
    assert len(result["jobs"]) == 3


def test_list_recent_jobs_with_status_filter():
    db = _session()
    _add_job(db, job_id="job-done-1", status="done")
    _add_job(db, job_id="job-queued-1", status="queued")
    result = execute_tool(db, tool_name="list_recent_jobs", tool_args={"status": "done", "limit": 5})
    assert all(j["status"] == "done" for j in result["jobs"])


def test_list_recent_jobs_limit_capped():
    db = _session()
    for i in range(5):
        _add_job(db, job_id=f"job-cap-{i}")
    result = execute_tool(db, tool_name="list_recent_jobs", tool_args={"limit": 100})
    assert len(result["jobs"]) <= 50


# ── get_metrics_snapshot ──────────────────────────────────────────────────────


def test_get_metrics_snapshot():
    db = _session()
    _add_job(db, job_id="job-m-1", status="queued")
    _add_job(db, job_id="job-m-2", status="done")
    result = execute_tool(db, tool_name="get_metrics_snapshot", tool_args={})
    assert "job_status_counts" in result
    assert "open_incidents" in result
    assert result["job_status_counts"].get("queued", 0) >= 1


# ── get_job_timeline ──────────────────────────────────────────────────────────


def test_get_job_timeline_empty():
    db = _session()
    _add_job(db, job_id="job-tl-1")
    result = execute_tool(db, tool_name="get_job_timeline", tool_args={"job_id": "job-tl-1"})
    assert result["job_id"] == "job-tl-1"
    assert result["events"] == []


def test_get_job_timeline_with_events():
    db = _session()
    _add_job(db, job_id="job-tl-2")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(RenderTimelineEvent(
        id="evt-1",
        job_id="job-tl-2",
        source="test",
        event_type="job_queued",
        status="queued",
        provider="veo",
        occurred_at=now,
    ))
    db.commit()
    result = execute_tool(db, tool_name="get_job_timeline", tool_args={"job_id": "job-tl-2"})
    assert len(result["events"]) == 1
    assert result["events"][0]["event_type"] == "job_queued"


def test_get_job_timeline_missing_job_id():
    db = _session()
    result = execute_tool(db, tool_name="get_job_timeline", tool_args={})
    assert "error" in result


# ── get_decision_engine_recommendations ──────────────────────────────────────


def test_get_decision_engine_recommendations():
    db = _session()
    result = execute_tool(db, tool_name="get_decision_engine_recommendations", tool_args={})
    assert "recommendations" in result
    assert isinstance(result["recommendations"], list)


# ── JSON string args ──────────────────────────────────────────────────────────


def test_tool_accepts_json_string_args():
    db = _session()
    _add_job(db, job_id="job-json-1", status="queued")
    import json
    result = execute_tool(
        db,
        tool_name="get_job_status",
        tool_args=json.dumps({"job_id": "job-json-1"}),
    )
    assert result["status"] == "queued"
