from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api import render_execution as render_execution_api
from app.db.session import get_db
from app.main import app
from app.services.project_render_runtime import trigger_project_render
from app.services.script_ingestion import build_preview_payload
from app.services.script_regeneration import recalculate_all_payload


def test_preview_payload_applies_execution_context() -> None:
    payload = build_preview_payload(
        filename="demo.txt",
        script_text="Intro line\n\nSecond line",
        aspect_ratio="9:16",
        target_platform="shorts",
        style_preset=None,
        avatar_id="avatar-123",
        market_code="vi-VN",
        content_goal="conversion",
        conversion_mode="aggressive",
    )

    assert payload["avatar_id"] == "avatar-123"
    assert payload["market_code"] == "vi-VN"
    assert payload["content_goal"] == "conversion"
    assert payload["conversion_mode"] == "aggressive"
    assert payload["scenes"][0]["metadata"]["execution_context"]["avatar_id"] == "avatar-123"
    assert payload["scenes"][0]["metadata"]["cta_bias"] == "aggressive"
    assert "Goal: conversion content" in payload["scenes"][0]["visual_prompt"]


def test_project_render_runtime_bridges_scene_prompts(monkeypatch) -> None:
    captured: dict[str, object] = {}
    saved: dict[str, object] = {}

    project = {
        "id": "project-1",
        "status": "ready_to_render",
        "provider": "veo_3_1",
        "format": "9:16",
        "content_goal": "conversion",
        "conversion_mode": "hard_sell",
        "scenes": [
            {
                "scene_index": 1,
                "title": "Scene 1",
                "script_text": "Present a limited-time bundle.",
                "target_duration_sec": 5.0,
            }
        ],
        "subtitle_segments": [
            {"scene_index": 1, "text": "Present a limited-time bundle.", "start_sec": 0.0, "end_sec": 2.0}
        ],
    }

    monkeypatch.setattr("app.services.project_render_runtime.load_project", lambda _project_id: project)
    monkeypatch.setattr("app.services.project_render_runtime.save_project", lambda p: saved.update({"project": p}))
    monkeypatch.setattr("app.services.project_render_runtime.enqueue_render_dispatch", lambda _job_id: {"task_id": "t-1"})

    def _fake_create_render_job_with_scenes(*args, **kwargs):
        captured["planned_scenes"] = kwargs["planned_scenes"]
        return SimpleNamespace(id="job-1")

    monkeypatch.setattr(
        "app.services.project_render_runtime.create_render_job_with_scenes",
        _fake_create_render_job_with_scenes,
    )

    result = trigger_project_render(db=None, project_id="project-1")

    assert result["render_job_id"] == "job-1"
    planned = captured["planned_scenes"][0]
    assert "Goal: conversion content" in planned["prompt_text"]
    assert planned["metadata"]["cta_bias"] == "hard_sell"
    assert saved["project"]["render_job_id"] == "job-1"


def test_render_job_route_transforms_scene_payload_by_context(monkeypatch) -> None:
    captured: dict[str, object] = {}
    client = TestClient(app)

    class DummyJob(SimpleNamespace):
        pass

    job = DummyJob(
        id="job-1",
        project_id="project-1",
        provider="veo",
        status="queued",
        aspect_ratio="9:16",
        style_preset=None,
        subtitle_mode="soft",
        planned_scene_count=1,
        completed_scene_count=0,
        failed_scene_count=0,
    )

    def _fake_db():
        yield object()

    def _fake_create_render_job_with_scenes(_db, **kwargs):
        captured["planned_scenes"] = kwargs["planned_scenes"]
        return job

    monkeypatch.setattr(render_execution_api, "get_or_create_global_kill_switch", lambda _db: SimpleNamespace(enabled=False, reason=None))
    monkeypatch.setattr(render_execution_api, "get_or_create_release_gate", lambda _db: SimpleNamespace(blocked=False, reason=None))
    monkeypatch.setattr(render_execution_api, "normalize_provider_name", lambda value: value)
    monkeypatch.setattr(render_execution_api, "create_render_job_with_scenes", _fake_create_render_job_with_scenes)
    monkeypatch.setattr(render_execution_api, "get_render_job_by_id", lambda _db, _job_id, with_scenes=False: job)
    monkeypatch.setattr(render_execution_api, "enqueue_render_dispatch", lambda _job_id: {"task_id": "dispatch-1"})
    monkeypatch.setattr(render_execution_api._avatar_usage_service, "track_use", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        render_execution_api._execution_bridge,
        "resolve_context",
        lambda *args, **kwargs: {
            "avatar_id": None,
            "market_code": "vi-VN",
            "content_goal": "conversion",
            "conversion_mode": "hard_sell",
            "avatar": None,
            "market": None,
            "template_family": None,
        },
    )
    app.dependency_overrides[get_db] = _fake_db

    try:
        response = client.post(
            "/api/v1/render/jobs",
            json={
                "project_id": "project-1",
                "provider": "veo",
                "aspect_ratio": "9:16",
                "subtitle_mode": "soft",
                "content_goal": "conversion",
                "conversion_mode": "hard_sell",
                "planned_scenes": [
                    {
                        "scene_index": 1,
                        "title": "Scene 1",
                        "script_text": "Show the product value clearly.",
                    }
                ],
            },
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    planned_scene = captured["planned_scenes"][0]
    assert "Goal: conversion content" in planned_scene["resolved_prompt_text"]
    assert planned_scene["metadata"]["cta_bias"] == "hard_sell"


def test_script_regeneration_preserves_execution_context() -> None:
    payload = {
        "avatar_id": "avatar-999",
        "market_code": "en-US",
        "content_goal": "conversion",
        "conversion_mode": "retargeting",
        "source_mode": "script_upload",
        "aspect_ratio": "9:16",
        "target_platform": "shorts",
        "style_preset": None,
        "original_filename": "demo.txt",
        "script_text": "Line one",
        "scenes": [
            {
                "scene_index": 1,
                "title": "Scene 1",
                "script_text": "Line one",
                "target_duration_sec": 5.0,
                "metadata": {},
            }
        ],
        "subtitle_segments": [
            {"scene_index": 1, "text": "Line one", "start_sec": 0.0, "end_sec": 1.5}
        ],
    }

    updated = recalculate_all_payload(payload)

    assert updated["avatar_id"] == "avatar-999"
    assert updated["market_code"] == "en-US"
    assert updated["content_goal"] == "conversion"
    assert updated["conversion_mode"] == "retargeting"
    assert updated["scenes"][0]["metadata"]["execution_context"]["avatar_id"] == "avatar-999"
    assert updated["scenes"][0]["metadata"]["cta_bias"] == "retargeting"
    assert "avatar-999" in updated["scenes"][0]["visual_prompt"]
