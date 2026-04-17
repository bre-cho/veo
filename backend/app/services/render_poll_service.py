from __future__ import annotations

from app.schemas.provider_common import NormalizedStatusResult
from app.services.provider_normalize import normalize_provider_name
from app.services.provider_router import query_render_task


async def poll_scene_task(
    *,
    provider: str,
    provider_task_id: str | None,
    provider_operation_name: str | None,
) -> NormalizedStatusResult:
    """
    Poll Veo trạng thái scene task theo normalized contract.

    Quy ước:
    - Veo dùng provider_operation_name
    - Kết quả luôn trả về NormalizedStatusResult
    - Nếu provider query lỗi, trả về state='failed' để worker quyết định xử lý tiếp
    """
    normalized_provider = normalize_provider_name(provider)

    if not provider_operation_name:
        return NormalizedStatusResult(
            provider=normalized_provider,
            state="failed",
            error_message="Missing provider_operation_name for Veo poll",
            failure_code="MISSING_PROVIDER_OPERATION_NAME",
            failure_category="orchestration",
            raw_response=None,
        )

    try:
        result = await query_render_task(
            provider=normalized_provider,
            provider_task_id=provider_task_id,
            provider_operation_name=provider_operation_name,
        )

        # Safety normalize tối thiểu nếu downstream provider trả thiếu trường
        return NormalizedStatusResult(
            provider=result.provider or normalized_provider,
            state=result.state,
            provider_status_raw=result.provider_status_raw,
            output_video_url=result.output_video_url,
            output_thumbnail_url=result.output_thumbnail_url,
            metadata=result.metadata,
            error_message=result.error_message,
            failure_code=result.failure_code,
            failure_category=result.failure_category,
            raw_response=result.raw_response,
        )

    except Exception as exc:
        return NormalizedStatusResult(
            provider=normalized_provider,
            state="failed",
            error_message=str(exc),
            failure_code="POLL_EXCEPTION",
            failure_category="provider_poll",
            raw_response=None,
        )