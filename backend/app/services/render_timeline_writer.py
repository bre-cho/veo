from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.render_scene_task import RenderSceneTask
from app.models.render_timeline_event import RenderTimelineEvent


_PRODUCTION_ALLOWED_STATUS = {
    "queued",
    "running",
    "succeeded",
    "failed",
    "blocked",
    "retried",
    "needs_review",
}


def _to_production_status(status: str | None) -> str:
    normalized = (status or "running").strip().lower()
    if normalized in _PRODUCTION_ALLOWED_STATUS:
        return normalized
    if normalized in {"completed", "success"}:
        return "succeeded"
    if normalized in {"error", "canceled", "cancelled", "queue_error"}:
        return "failed"
    if normalized in {"identity_review", "quality_remediation", "polling", "dispatching", "submitted", "processing", "merging", "burning_subtitles"}:
        return "running"
    return "running"


def _to_production_phase(source: str) -> str:
    normalized = (source or "render").strip().lower()
    if normalized in {"operator", "factory"}:
        return "operator"
    if normalized == "publish":
        return "publish"
    if normalized in {"narration", "music", "mix", "mux", "ingest"}:
        return normalized
    return "render"


def _mirror_to_production_timeline(
    *,
    job_id: str,
    scene_index: int | None,
    source: str,
    event_type: str,
    status: str | None,
    provider: str | None,
    error_message: str | None,
    payload: dict[str, Any] | None,
    occurred_at: datetime,
) -> None:
    try:
        from app.state import timeline_service

        timeline_service.write_event(
            {
                "render_job_id": job_id,
                "title": event_type,
                "message": error_message,
                "phase": _to_production_phase(source),
                "stage": event_type,
                "event_type": event_type,
                "status": _to_production_status(status),
                "worker_name": source,
                "provider": provider,
                "is_blocking": _to_production_status(status) in {"failed", "blocked", "needs_review"},
                "is_operator_action": _to_production_phase(source) == "operator",
                "details": {
                    "scene_index": scene_index,
                    "source": source,
                    "payload": payload or {},
                },
                "occurred_at": occurred_at,
            }
        )
    except Exception:
        # Production timeline mirroring must not break render orchestration.
        return


def _dump(payload: dict[str, Any] | None) -> str | None:
    if payload is None:
        return None
    return json.dumps(payload, ensure_ascii=False)


def append_timeline_event(
    db: Session,
    *,
    job_id: str,
    scene_task_id: str | None,
    scene_index: int | None,
    source: str,
    event_type: str,
    occurred_at: datetime | None = None,
    status: str | None = None,
    provider: str | None = None,
    provider_status_raw: str | None = None,
    provider_request_id: str | None = None,
    provider_task_id: str | None = None,
    provider_operation_name: str | None = None,
    failure_code: str | None = None,
    failure_category: str | None = None,
    error_message: str | None = None,
    signature_valid: bool | None = None,
    processed: bool | None = None,
    event_idempotency_key: str | None = None,
    payload: dict[str, Any] | None = None,
    _flush_only: bool = False,
) -> RenderTimelineEvent:
    resolved_occurred_at = occurred_at or datetime.now(timezone.utc).replace(tzinfo=None)
    event = RenderTimelineEvent(
        id=f"rte_{uuid.uuid4().hex[:24]}",
        job_id=job_id,
        scene_task_id=scene_task_id,
        scene_index=scene_index,
        source=source,
        event_type=event_type,
        status=status,
        provider=provider,
        provider_status_raw=provider_status_raw,
        provider_request_id=provider_request_id,
        provider_task_id=provider_task_id,
        provider_operation_name=provider_operation_name,
        failure_code=failure_code,
        failure_category=failure_category,
        error_message=error_message,
        signature_valid=signature_valid,
        processed=processed,
        event_idempotency_key=event_idempotency_key,
        payload_json=_dump(payload),
        occurred_at=resolved_occurred_at,
    )
    db.add(event)
    if _flush_only:
        db.flush()
    else:
        db.commit()
        db.refresh(event)

    _mirror_to_production_timeline(
        job_id=job_id,
        scene_index=scene_index,
        source=source,
        event_type=event_type,
        status=status,
        provider=provider,
        error_message=error_message,
        payload=payload,
        occurred_at=resolved_occurred_at,
    )

    return event


def append_scene_timeline_event(
    db: Session,
    *,
    scene: RenderSceneTask,
    source: str,
    event_type: str,
    occurred_at: datetime | None = None,
    status: str | None = None,
    provider_status_raw: str | None = None,
    failure_code: str | None = None,
    failure_category: str | None = None,
    error_message: str | None = None,
    payload: dict[str, Any] | None = None,
) -> RenderTimelineEvent:
    return append_timeline_event(
        db,
        job_id=scene.job_id,
        scene_task_id=scene.id,
        scene_index=scene.scene_index,
        source=source,
        event_type=event_type,
        occurred_at=occurred_at,
        status=status or scene.status,
        provider=scene.provider,
        provider_status_raw=provider_status_raw or scene.provider_status_raw,
        provider_request_id=scene.provider_request_id,
        provider_task_id=scene.provider_task_id,
        provider_operation_name=scene.provider_operation_name,
        failure_code=failure_code,
        failure_category=failure_category,
        error_message=error_message,
        payload=payload,
    )
