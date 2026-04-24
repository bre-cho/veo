from __future__ import annotations

from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "render_factory",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.render_tasks",
        "app.workers.stuck_job_recovery_worker",
        "app.workers.template_analytics_worker",
        "app.workers.template_batch_worker",
        "app.workers.template_generation_worker",
        "app.workers.template_extraction_worker",
        "app.workers.template_rescore_worker",
        "app.workers.template_feedback_worker",
        "app.workers.autopilot_worker",
        "app.workers.narration_worker",
        "app.workers.audio_preview_worker",
        "app.workers.music_worker",
        "app.workers.audio_mix_worker",
        "app.workers.video_mux_worker",
        "app.workers.voice_clone_worker",
        "app.drama.workers.drama_scene_worker",
        "app.drama.workers.continuity_rebuild_worker",
        "app.drama.workers.drama_arc_worker",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=settings.celery_task_acks_late,
    worker_prefetch_multiplier=settings.celery_worker_prefetch_multiplier,
    task_time_limit=settings.celery_task_time_limit,
    task_soft_time_limit=settings.celery_task_soft_time_limit,
    worker_send_task_events=True,
    task_send_sent_event=True,
    timezone="UTC",
    enable_utc=True,
    # Route tasks to dedicated queues so separate worker pools can be
    # configured per queue (e.g. higher concurrency for poll, single worker
    # for postprocess, low-priority queue for template work).
    task_routes={
        "render.dispatch": {"queue": "render_dispatch"},
        "render.poll": {"queue": "render_poll"},
        "render.postprocess": {"queue": "render_postprocess"},
        "render.callback_process": {"queue": "render_callback"},
        "render.recover_stuck": {"queue": "render_maintenance"},
        "autopilot.evaluate_control_fabric": {"queue": "autopilot"},
        "audio.run_narration": {"queue": "audio"},
        "audio.run_preview": {"queue": "audio"},
        "audio.generate_music": {"queue": "audio"},
        "audio.mix_tracks": {"queue": "audio"},
        "audio.mux_video": {"queue": "audio"},
        "audio.clone_voice_profile": {"queue": "audio"},
        "app.workers.template_analytics_worker.run": {"queue": "template"},
        "app.workers.template_batch_worker.run": {"queue": "template"},
        "app.workers.template_generation_worker.run": {"queue": "template"},
        "app.workers.template_extraction_worker.run": {"queue": "template"},
        "app.workers.template_rescore_worker.run": {"queue": "template"},
        "app.workers.template_feedback_worker.run": {"queue": "template"},
        "app.drama.workers.process_scene": {"queue": "drama"},
        "app.drama.workers.rebuild_continuity": {"queue": "drama"},
        "app.drama.workers.recompute_arcs": {"queue": "drama"},
    },
    # Default queue for any task not explicitly routed above.
    task_default_queue="celery",
)

celery_app.conf.beat_schedule = {
    "recover-stuck-render-tasks": {
        "task": "render.recover_stuck",
        "schedule": 120.0,
    }
}

from celery.schedules import crontab

try:
    celery_app.conf.beat_schedule = {
        **getattr(celery_app.conf, "beat_schedule", {}),
        "autopilot-evaluate-control-fabric-every-5-minutes": {
            "task": "autopilot.evaluate_control_fabric",
            "schedule": 300.0,
        },
    }
except Exception:
    pass
