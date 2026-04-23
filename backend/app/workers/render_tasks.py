from __future__ import annotations

import asyncio

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.workers.render_dispatch_worker import process_render_dispatch
from app.workers.render_identity_review_worker import process_render_identity_review
from app.workers.render_poll_worker import process_render_poll
from app.workers.render_postprocess_worker import process_render_postprocess
from app.workers.provider_callback_worker import process_provider_callback_event


@celery_app.task(name="render.dispatch")
def render_dispatch_task(job_id: str) -> None:
    db = SessionLocal()
    try:
        asyncio.run(process_render_dispatch(db, job_id))
    finally:
        db.close()


@celery_app.task(name="render.poll")
def render_poll_task(job_id: str, scene_task_id: str) -> None:
    db = SessionLocal()
    try:
        asyncio.run(process_render_poll(db, job_id, scene_task_id))
    finally:
        db.close()


@celery_app.task(name="render.postprocess")
def render_postprocess_task(job_id: str) -> None:
    db = SessionLocal()
    try:
        asyncio.run(process_render_postprocess(db, job_id))
    finally:
        db.close()


@celery_app.task(name="render.identity_review")
def render_identity_review_task(job_id: str) -> None:
    db = SessionLocal()
    try:
        asyncio.run(process_render_identity_review(db, job_id))
    finally:
        db.close()


@celery_app.task(name="render.callback_process")
def render_callback_process_task(event_id: str) -> None:
    db = SessionLocal()
    try:
        asyncio.run(process_provider_callback_event(db, event_id))
    finally:
        db.close()

