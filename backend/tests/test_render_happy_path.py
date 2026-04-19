"""Happy-path end-to-end render pipeline integration test.

Covers the full lifecycle:
  1. Create project + render job + scene tasks
  2. Dispatch: job queued → dispatching → polling, scenes queued → submitted
  3. Provider poll callback: scene submitted → succeeded
  4. All scenes succeeded → finalize job → completed
  5. Assert: job status = completed, output URL set, timeline events recorded
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker, Session

from app.db.base import Base
from app.models.render_job import RenderJob
from app.models.render_scene_task import RenderSceneTask

import app.services.render_repository as repo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# SQLite in-memory DB fixture  (enables FK enforcement)
# ---------------------------------------------------------------------------

@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    # Enable FK support for SQLite
    @sa_event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _conn_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False)
    session = SessionLocal()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Happy-path test
# ---------------------------------------------------------------------------

def test_render_happy_path_single_scene(db: Session) -> None:
    """Full render lifecycle: create → dispatch → poll success → finalize."""

    project_id = _uuid()
    planned_scenes = [
        {
            "scene_index": 0,
            "title": "Opening shot",
            "prompt": "A sunrise over mountains",
            "duration_sec": 5,
        }
    ]

    # ------------------------------------------------------------------
    # 1. Create render job
    # ------------------------------------------------------------------
    job = repo.create_render_job_with_scenes(
        db,
        project_id=project_id,
        provider="veo",
        aspect_ratio="16:9",
        style_preset=None,
        subtitle_mode="none",
        planned_scenes=planned_scenes,
    )

    assert job is not None
    assert job.status == "queued"
    assert len(job.scenes) == 1
    scene = job.scenes[0]
    assert scene.status == "queued"
    assert scene.scene_index == 0

    # ------------------------------------------------------------------
    # 2. Dispatch: queued → dispatching
    # ------------------------------------------------------------------
    dispatched = repo.mark_job_status(
        db,
        job=job,
        status="dispatching",
        source="dispatch_worker",
        reason="Dispatch started",
    )
    assert dispatched is True
    db.refresh(job)
    assert job.status == "dispatching"

    # ------------------------------------------------------------------
    # 3. Scene submitted to provider
    # ------------------------------------------------------------------
    provider_task_id = "operations/abc123"
    submitted = repo.mark_scene_submitted(
        db,
        scene=scene,
        provider_task_id=provider_task_id,
        provider_operation_name=provider_task_id,
        provider_request_id="req-001",
        raw_response={"name": provider_task_id},
        source="dispatch",
    )
    assert submitted is True
    db.refresh(scene)
    assert scene.status == "submitted"
    assert scene.provider_task_id == provider_task_id

    # Job advances to polling
    polled = repo.mark_job_status(
        db,
        job=job,
        status="polling",
        source="dispatch_worker",
        reason="All scenes submitted",
    )
    assert polled is True
    db.refresh(job)
    assert job.status == "polling"

    # ------------------------------------------------------------------
    # 4. Provider poll returns success
    # ------------------------------------------------------------------
    output_url = "https://storage.example.com/videos/output.mp4"
    thumb_url = "https://storage.example.com/videos/output_thumb.jpg"

    db.refresh(scene)
    succeeded = repo.transition_scene_to_succeeded(
        db,
        job=job,
        scene=scene,
        provider_status_raw="SUCCEEDED",
        output_video_url=output_url,
        output_thumbnail_url=thumb_url,
        source="poll",
    )
    assert succeeded is True
    db.refresh(scene)
    assert scene.status == "succeeded"
    assert scene.output_video_url == output_url
    assert scene.output_thumbnail_url == thumb_url
    assert scene.finished_at is not None

    # ------------------------------------------------------------------
    # 5. All scenes done → finalize job
    # ------------------------------------------------------------------
    db.refresh(job)
    final_url = "https://storage.example.com/videos/final_merged.mp4"
    final_path = "/mnt/render_output/final_merged.mp4"
    finalized = repo.finalize_render_job(
        db,
        job=job,
        final_video_url=final_url,
        final_video_path=final_path,
        final_timeline={"scenes": [{"index": 0, "url": output_url}]},
        source="postprocess",
    )
    assert finalized is True
    db.refresh(job)
    assert job.status == "completed"
    assert job.final_video_url == final_url
    assert job.final_video_path == final_path

    # ------------------------------------------------------------------
    # 6. Timeline events recorded
    # ------------------------------------------------------------------
    events = repo.list_timeline_events_for_job(db, job.id)
    event_types = {e.event_type for e in events}
    assert "scene_succeeded" in event_types, f"Missing scene_succeeded. Got: {event_types}"
    assert "job_completed" in event_types, f"Missing job_completed. Got: {event_types}"


def test_render_happy_path_multi_scene(db: Session) -> None:
    """Happy-path with 3 scenes: all succeed, job completes."""

    project_id = _uuid()
    planned_scenes = [
        {"scene_index": i, "title": f"Scene {i}", "prompt": f"Shot {i}", "duration_sec": 4}
        for i in range(3)
    ]

    job = repo.create_render_job_with_scenes(
        db,
        project_id=project_id,
        provider="veo",
        aspect_ratio="9:16",
        style_preset="cinematic",
        subtitle_mode="none",
        planned_scenes=planned_scenes,
    )

    assert job.status == "queued"
    assert len(job.scenes) == 3

    # Dispatch
    repo.mark_job_status(db, job=job, status="dispatching", source="dispatch_worker", reason="")
    for scene in job.scenes:
        repo.mark_scene_submitted(
            db,
            scene=scene,
            provider_task_id=f"operations/scene-{scene.scene_index}",
            provider_operation_name=f"operations/scene-{scene.scene_index}",
            provider_request_id=f"req-{scene.scene_index}",
            raw_response={"name": f"operations/scene-{scene.scene_index}"},
            source="dispatch",
        )
    repo.mark_job_status(db, job=job, status="polling", source="dispatch_worker", reason="")

    # All scenes succeed via poll
    db.refresh(job)
    for scene in job.scenes:
        db.refresh(scene)
        repo.transition_scene_to_succeeded(
            db,
            job=job,
            scene=scene,
            provider_status_raw="SUCCEEDED",
            output_video_url=f"https://cdn.example.com/scene-{scene.scene_index}.mp4",
            output_thumbnail_url=None,
            source="poll",
        )

    # Finalize
    db.refresh(job)
    finalized = repo.finalize_render_job(
        db,
        job=job,
        final_video_url="https://cdn.example.com/final.mp4",
        final_video_path="/output/final.mp4",
        final_timeline={"scene_count": 3},
        source="postprocess",
    )
    assert finalized is True
    db.refresh(job)
    assert job.status == "completed"
    assert job.completed_scene_count == 3

    events = repo.list_timeline_events_for_job(db, job.id)
    assert any(e.event_type == "job_completed" for e in events)


def test_render_fsm_invalid_transition_is_rejected(db: Session) -> None:
    """FSM rejects an invalid state transition (queued → completed directly)."""

    project_id = _uuid()
    job = repo.create_render_job_with_scenes(
        db,
        project_id=project_id,
        provider="veo",
        aspect_ratio="16:9",
        style_preset=None,
        subtitle_mode="none",
        planned_scenes=[{"scene_index": 0, "title": "T", "prompt": "P", "duration_sec": 5}],
    )
    assert job.status == "queued"

    # Attempting queued → completed directly is invalid
    result = repo.finalize_render_job(
        db,
        job=job,
        final_video_url="https://cdn.example.com/out.mp4",
        final_video_path="/out.mp4",
        final_timeline={},
        source="postprocess",
    )
    assert result is False, "Invalid transition should be rejected by FSM"
    db.refresh(job)
    assert job.status == "queued", "Status should remain unchanged after rejected transition"
