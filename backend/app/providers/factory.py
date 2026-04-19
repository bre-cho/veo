from __future__ import annotations

import json
from typing import Any, Protocol

from app.core.config import settings
from app.services.provider_router import query_render_task, submit_render_task


class ProviderClientProtocol(Protocol):
    async def dispatch_scene(self, *, job: Any, scene_task: Any) -> dict[str, Any]:
        ...

    async def poll_scene(
        self,
        *,
        provider_task_id: str | None,
        provider_operation_name: str | None,
        scene_task: Any,
        job: Any,
    ) -> dict[str, Any]:
        ...


class MockProviderClient:
    """
    Mock production-safe client để pipeline chạy kín local/dev.
    Có thể thay bằng VeoProviderClient thật sau.
    """

    async def dispatch_scene(self, *, job: Any, scene_task: Any) -> dict[str, Any]:
        return {
            "status": "submitted",
            "provider_task_id": f"mock-task-{scene_task.id}",
            "provider_operation_name": f"mock-op-{scene_task.id}",
            "provider_payload": {
                "provider": getattr(job, "provider", "mock"),
                "scene_index": getattr(scene_task, "scene_index", None),
            },
        }

    async def poll_scene(
        self,
        *,
        provider_task_id: str | None,
        provider_operation_name: str | None,
        scene_task: Any,
        job: Any,
    ) -> dict[str, Any]:
        output_path = getattr(scene_task, "mock_output_path", None) or getattr(scene_task, "output_path", None)

        return {
            "status": "succeeded",
            "provider_task_id": provider_task_id,
            "provider_operation_name": provider_operation_name,
            "output_url": None,
            "output_path": output_path,
            "provider_payload": {
                "provider": getattr(job, "provider", "mock"),
                "provider_task_id": provider_task_id,
                "provider_operation_name": provider_operation_name,
            },
            "error_message": None,
        }


class VeoProviderClient:
    async def dispatch_scene(self, *, job: Any, scene_task: Any) -> dict[str, Any]:
        payload_raw = getattr(scene_task, "request_payload_json", None)
        if isinstance(payload_raw, dict):
            payload = payload_raw
        else:
            try:
                payload = json.loads(payload_raw or "{}")
            except (TypeError, ValueError):
                payload = {}

        result = await submit_render_task(
            provider=getattr(job, "provider", "veo"),
            scene_payload=payload,
            callback_url=None,
        )
        return {
            "status": "submitted" if result.accepted else "failed",
            "provider_task_id": result.provider_task_id,
            "provider_operation_name": result.provider_operation_name,
            "provider_payload": result.raw_response,
            "error_message": result.error_message,
        }

    async def poll_scene(
        self,
        *,
        provider_task_id: str | None,
        provider_operation_name: str | None,
        scene_task: Any,
        job: Any,
    ) -> dict[str, Any]:
        result = await query_render_task(
            provider=getattr(job, "provider", "veo"),
            provider_task_id=provider_task_id,
            provider_operation_name=provider_operation_name,
        )
        return {
            "status": result.state,
            "provider_task_id": provider_task_id,
            "provider_operation_name": provider_operation_name,
            "output_url": result.output_video_url,
            "output_path": getattr(scene_task, "output_path", None),
            "provider_payload": result.raw_response,
            "error_message": result.error_message,
            "failure_code": result.failure_code,
            "failure_category": result.failure_category,
        }


def get_provider_client(provider_name: str) -> ProviderClientProtocol:
    normalized = str(provider_name or "").strip().lower()
    app_env = settings.app_env.strip().lower()
    allow_mock = bool(settings.provider_allow_mock_fallback) and app_env in {"development", "test", "testing", "local"}

    if normalized in {"veo", "veo_3", "veo_3_1"}:
        return VeoProviderClient()
    if allow_mock:
        return MockProviderClient()
    if bool(settings.provider_allow_mock_fallback):
        raise ValueError(
            f"Unsupported provider: {provider_name}; mock fallback is only allowed in development/test environments."
        )
    raise ValueError(
        f"Unsupported provider: {provider_name}; mock fallback is disabled for environment '{settings.app_env}'."
    )
