from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.provider_ingress_signing import (
    resolve_ingress_secret,
    verify_ingress_signature,
)
from app.services.provider_router import (
    normalize_render_callback,
    verify_render_callback,
)
from app.services.render_queue import enqueue_render_callback_process
from app.services.render_repository import (
    create_webhook_event,
    find_scene_by_provider_refs,
)

router = APIRouter(prefix="/api/v1/provider-callbacks", tags=["provider-callbacks"])
logger = logging.getLogger(__name__)


def _load_json_payload(raw_body: bytes) -> dict:
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON payload: {exc}",
        ) from exc
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Callback payload must be a JSON object",
        )
    return payload


async def _process_normalized_callback(*, provider_key: str, headers: dict[str, str], payload: dict):
    normalized = normalize_render_callback(
        provider=provider_key,
        headers=headers,
        payload=payload,
    )

    db: Session = SessionLocal()
    try:
        scene = find_scene_by_provider_refs(
            db,
            provider=provider_key,
            provider_task_id=normalized.provider_task_id,
            provider_operation_name=normalized.provider_operation_name,
        )

        event, created = create_webhook_event(
            db,
            provider=provider_key,
            event_type=normalized.event_type,
            event_idempotency_key=normalized.event_idempotency_key,
            scene_task_id=scene.id if scene else None,
            provider_task_id=normalized.provider_task_id,
            provider_operation_name=normalized.provider_operation_name,
            signature_valid=True,
            headers_json=headers,
            payload_json=payload,
            normalized_payload_json=normalized.model_dump(),
        )
        if not created:
            return {
                "ok": True,
                "duplicate": True,
                "event_id": event.id,
                "event_idempotency_key": normalized.event_idempotency_key,
            }

        enqueue_render_callback_process(event.id)
        logger.info(
            "provider_callback_enqueued",
            extra={
                "provider": provider_key,
                "event_id": event.id,
                "event_idempotency_key": normalized.event_idempotency_key,
                "scene_task_id": scene.id if scene else None,
            },
        )

        return {
            "ok": True,
            "duplicate": False,
            "event_id": event.id,
            "scene_matched": scene is not None,
            "scene_task_id": scene.id if scene else None,
            "event_idempotency_key": normalized.event_idempotency_key,
            "normalized_state": normalized.state,
            "enqueued": True,
        }
    finally:
        db.close()


@router.post("/{provider}")
async def receive_provider_callback(provider: str, request: Request):
    raw_body = await request.body()
    payload = _load_json_payload(raw_body)
    headers = {k.lower(): v for k, v in request.headers.items()}
    provider_key = provider.strip().lower()

    signature_valid = verify_render_callback(
        provider=provider_key,
        headers=headers,
        raw_body=raw_body,
    )
    if not signature_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid callback signature",
        )

    return await _process_normalized_callback(
        provider_key=provider_key,
        headers=headers,
        payload=payload,
    )


@router.post("/relay/{provider}")
async def receive_provider_callback_from_signed_relay(provider: str, request: Request):
    raw_body = await request.body()
    payload = _load_json_payload(raw_body)
    headers = {k.lower(): v for k, v in request.headers.items()}
    provider_key = provider.strip().lower()

    relay_secret = resolve_ingress_secret(provider_key)
    signature_valid = verify_ingress_signature(
        secret=relay_secret,
        timestamp=headers.get("x-render-relay-timestamp"),
        signature=headers.get("x-render-relay-signature"),
        raw_body=raw_body,
    )
    if not signature_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid relay signature",
        )

    return await _process_normalized_callback(
        provider_key=provider_key,
        headers=headers,
        payload=payload,
    )
