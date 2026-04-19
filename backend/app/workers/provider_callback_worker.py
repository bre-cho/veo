from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.provider_webhook_event import ProviderWebhookEvent
from app.schemas.provider_common import NormalizedCallbackEvent
from app.services.asset_collector import cache_remote_video
from app.services.render_repository import (
    find_scene_by_provider_refs,
    get_render_job_by_id,
    is_scene_terminal,
    mark_webhook_event_processed,
    should_enqueue_postprocess,
    transition_scene_to_failed,
    transition_scene_to_processing,
    transition_scene_to_succeeded,
)


async def process_provider_callback_event(db: Session, event_id: str) -> None:
    from app.services.render_queue import enqueue_render_postprocess

    event = db.query(ProviderWebhookEvent).filter(ProviderWebhookEvent.id == event_id).first()
    if not event or event.processed:
        return

    normalized_data = json.loads(event.normalized_payload_json or "{}")
    normalized = NormalizedCallbackEvent.model_validate(normalized_data)

    scene = find_scene_by_provider_refs(
        db,
        provider=event.provider,
        provider_task_id=normalized.provider_task_id,
        provider_operation_name=normalized.provider_operation_name,
    )

    if scene is None or is_scene_terminal(scene):
        mark_webhook_event_processed(db, event)
        return

    transitioned = False
    if normalized.state == "processing":
        transitioned = transition_scene_to_processing(
            db,
            scene,
            provider_status_raw=normalized.provider_status_raw,
            metadata=normalized.metadata,
            raw_response=normalized.raw_payload,
            source="callback",
        )
    elif normalized.state == "succeeded":
        job = scene.job
        local_video_path = None
        if normalized.output_video_url:
            local_video_path = await cache_remote_video(
                job_id=scene.job_id,
                scene_index=scene.scene_index,
                url=normalized.output_video_url,
            )
        transitioned = transition_scene_to_succeeded(
            db,
            job,
            scene,
            provider_status_raw=normalized.provider_status_raw,
            output_video_url=normalized.output_video_url,
            output_thumbnail_url=normalized.output_thumbnail_url,
            local_video_path=local_video_path,
            metadata=normalized.metadata,
            raw_response=normalized.raw_payload,
            source="callback",
        )
        if transitioned:
            refreshed_job = get_render_job_by_id(db, scene.job_id, with_scenes=False)
            if refreshed_job and should_enqueue_postprocess(refreshed_job):
                enqueue_render_postprocess(refreshed_job.id)
    elif normalized.state in {"failed", "canceled"}:
        job = scene.job
        transitioned = transition_scene_to_failed(
            db,
            job,
            scene,
            provider_status_raw=normalized.provider_status_raw,
            error_message=normalized.error_message or normalized.state,
            failure_code=normalized.failure_code,
            failure_category=normalized.failure_category,
            raw_response=normalized.raw_payload,
            source="callback",
            final_status="canceled" if normalized.state == "canceled" else "failed",
        )
        if transitioned:
            refreshed_job = get_render_job_by_id(db, scene.job_id, with_scenes=False)
            if refreshed_job and should_enqueue_postprocess(refreshed_job):
                enqueue_render_postprocess(refreshed_job.id)

    mark_webhook_event_processed(db, event)
