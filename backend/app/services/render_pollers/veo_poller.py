from __future__ import annotations

from app.providers.veo.adapter import VeoAdapter
from .types import PollResult

_adapter = VeoAdapter()


async def poll_veo_operation(operation_name: str) -> PollResult:
    """Poll the status of a Veo operation via VeoAdapter."""
    result = await _adapter.query(
        provider_task_id=None,
        provider_operation_name=operation_name,
    )
    return PollResult(
        state=result.state,
        output_video_url=result.output_video_url,
        output_thumbnail_url=result.output_thumbnail_url,
        raw_response=result.raw_response,
        error_message=result.error_message,
    )
