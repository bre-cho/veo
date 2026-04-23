from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.render_queue import enqueue_render_dispatch
from app.services.control_plane import get_or_create_release_gate
from app.services.kill_switch import get_or_create_global_kill_switch
from app.services.provider_normalize import normalize_provider_name
from app.services.execution_bridge_service import ExecutionBridgeService
from app.services.render_repository import (
    create_render_job_with_scenes,
    get_render_job_by_id,
)
from app.services.marketplace.avatar_usage_service import AvatarUsageService

_log = logging.getLogger(__name__)
_avatar_usage_service = AvatarUsageService()
_execution_bridge = ExecutionBridgeService()

router = APIRouter(prefix="/api/v1/render", tags=["render-execution"])


# =========================
# Request schemas
# =========================
class PlannedSceneCreateRequest(BaseModel):
    scene_index: int = Field(..., ge=1)
    title: str = Field(..., min_length=1)

    # prompt/script
    script_text: str | None = None
    prompt_text: str | None = None
    prompt: str | None = None

    # provider shaping
    provider_model: str | None = None
    provider_target_duration_sec: int | None = Field(default=None, ge=1, le=60)
    duration_seconds: int | None = Field(default=None, ge=1, le=60)
    aspect_ratio: str | None = None
    negative_prompt: str | None = None
    seed: int | None = None
    enable_audio: bool = False

    # image-to-video inputs
    prompt_image_url: str | None = None
    prompt_image_gcs_uri: str | None = None
    last_frame_image_url: str | None = None
    last_frame_image_gcs_uri: str | None = None

    # extra metadata for future flexibility
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, value: str | None) -> str | None:
        if value is None:
            return value
        allowed = {"16:9", "9:16", "1:1"}
        if value not in allowed:
            raise ValueError(f"aspect_ratio must be one of {sorted(allowed)}")
        return value

    def to_repository_payload(self, job_provider: str, job_aspect_ratio: str) -> dict[str, Any]:
        """
        Chuẩn hóa scene payload để lưu vào request_payload_json.
        File render_dispatch_service.py sẽ đọc các key này để build provider payload thật.
        """
        resolved_prompt_text = (
            self.prompt_text
            or self.script_text
            or self.prompt
            or ""
        )

        resolved_duration = (
            self.duration_seconds
            or self.provider_target_duration_sec
            or 5
        )

        return {
            "scene_index": self.scene_index,
            "title": self.title,
            "provider": job_provider,
            "provider_model": self.provider_model,
            "script_text": self.script_text,
            "prompt_text": self.prompt_text,
            "prompt": self.prompt,
            "resolved_prompt_text": resolved_prompt_text,
            "provider_target_duration_sec": self.provider_target_duration_sec,
            "duration_seconds": self.duration_seconds,
            "resolved_duration_seconds": resolved_duration,
            "aspect_ratio": self.aspect_ratio or job_aspect_ratio,
            "negative_prompt": self.negative_prompt,
            "seed": self.seed,
            "enable_audio": self.enable_audio,
            "prompt_image_url": self.prompt_image_url,
            "prompt_image_gcs_uri": self.prompt_image_gcs_uri,
            "last_frame_image_url": self.last_frame_image_url,
            "last_frame_image_gcs_uri": self.last_frame_image_gcs_uri,
            "metadata": self.metadata,
        }


class RenderJobCreateRequest(BaseModel):
    project_id: str = Field(..., min_length=1)
    provider: str = Field(..., min_length=1)
    aspect_ratio: str = Field(default="16:9")
    style_preset: str | None = None
    subtitle_mode: str = Field(default="soft")
    planned_scenes: list[PlannedSceneCreateRequest] = Field(..., min_length=1)

    # --- Autovis commerce context (optional, backward-compatible) ---
    avatar_id: str | None = None
    market_code: str | None = None
    content_goal: str | None = None
    conversion_mode: str | None = None
    # --- Brain Layer context (optional) ---
    series_id: str | None = None
    episode_index: int | None = None
    continuity_context: dict[str, Any] | None = None
    winner_dna_summary: dict[str, Any] | None = None
    brain_plan: dict[str, Any] | None = None

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {
            "veo",
            "veo_3",
            "veo_3_1",
            "google_veo",
        }
        if normalized not in allowed:
            raise ValueError(f"provider must be one of {sorted(allowed)}")
        return normalized

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, value: str) -> str:
        allowed = {"16:9", "9:16", "1:1"}
        if value not in allowed:
            raise ValueError(f"aspect_ratio must be one of {sorted(allowed)}")
        return value

    @field_validator("subtitle_mode")
    @classmethod
    def validate_subtitle_mode(cls, value: str) -> str:
        allowed = {"soft", "burn", "none"}
        if value not in allowed:
            raise ValueError(f"subtitle_mode must be one of {sorted(allowed)}")
        return value

    @field_validator("planned_scenes")
    @classmethod
    def validate_planned_scenes(cls, value: list[PlannedSceneCreateRequest]) -> list[PlannedSceneCreateRequest]:
        if not value:
            raise ValueError("planned_scenes must not be empty")

        scene_indexes = [scene.scene_index for scene in value]
        if len(scene_indexes) != len(set(scene_indexes)):
            raise ValueError("scene_index values must be unique")

        return sorted(value, key=lambda s: s.scene_index)


# =========================
# Response schemas
# =========================
class RenderJobCreateResponse(BaseModel):
    id: str
    project_id: str
    provider: str
    status: str
    aspect_ratio: str
    style_preset: str | None = None
    subtitle_mode: str
    planned_scene_count: int
    completed_scene_count: int
    failed_scene_count: int
    dispatch_task: dict[str, Any]


# =========================
# Routes
# =========================
@router.post(
    "/jobs",
    response_model=RenderJobCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_render_job(
    payload: RenderJobCreateRequest,
    db: Session = Depends(get_db),
):
    kill_switch = get_or_create_global_kill_switch(db)
    if kill_switch.enabled:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Global kill switch is enabled: {kill_switch.reason or 'blocked by control plane'}",
        )

    release_gate = get_or_create_release_gate(db)
    if release_gate.blocked:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Release gate is blocked: {release_gate.reason or 'blocked by control plane'}",
        )

    normalized_provider = normalize_provider_name(payload.provider)
    bridge_ctx = _execution_bridge.resolve_context(
        db,
        avatar_id=payload.avatar_id,
        market_code=payload.market_code,
        content_goal=payload.content_goal,
        conversion_mode=payload.conversion_mode,
        series_id=payload.series_id,
        episode_index=payload.episode_index,
        continuity_context=payload.continuity_context,
        winner_dna_summary=payload.winner_dna_summary,
        brain_plan=payload.brain_plan,
    )

    planned_scenes = [
        _execution_bridge.transform_scene_payload(
            scene.to_repository_payload(
                job_provider=normalized_provider,
                job_aspect_ratio=payload.aspect_ratio,
            ),
            bridge_ctx,
        )
        for scene in payload.planned_scenes
    ]

    try:
        job = create_render_job_with_scenes(
            db,
            project_id=payload.project_id,
            provider=normalized_provider,
            aspect_ratio=payload.aspect_ratio,
            style_preset=payload.style_preset,
            subtitle_mode=payload.subtitle_mode,
            planned_scenes=planned_scenes,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create render job: {exc}",
        ) from exc

    if not job:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Render job was not created",
        )

    try:
        dispatch_task = enqueue_render_dispatch(job.id)
    except Exception as exc:
        # Job đã tạo trong DB rồi nhưng enqueue lỗi -> update trạng thái lỗi nhẹ cho dễ debug
        reloaded = get_render_job_by_id(db, job.id, with_scenes=False)
        if reloaded:
            reloaded.status = "queue_error"
            reloaded.error_message = f"Failed to enqueue render dispatch: {exc}"
            db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Render job created but dispatch enqueue failed: {exc}",
        ) from exc

    refreshed = get_render_job_by_id(db, job.id, with_scenes=False)
    if not refreshed:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Render job created but could not be reloaded",
        )

    response = RenderJobCreateResponse(
        id=refreshed.id,
        project_id=refreshed.project_id,
        provider=refreshed.provider,
        status=refreshed.status,
        aspect_ratio=refreshed.aspect_ratio,
        style_preset=refreshed.style_preset,
        subtitle_mode=refreshed.subtitle_mode,
        planned_scene_count=refreshed.planned_scene_count,
        completed_scene_count=refreshed.completed_scene_count,
        failed_scene_count=refreshed.failed_scene_count,
        dispatch_task=dispatch_task,
    )

    # --- Autovis production bridge: track avatar usage after job is dispatched ---
    if payload.avatar_id:
        try:
            _avatar_usage_service.track_use(
                db,
                avatar_id=payload.avatar_id,
                user_id=None,
                render_job_id=refreshed.id,
                meta={
                    "market_code": payload.market_code,
                    "content_goal": payload.content_goal,
                    "conversion_mode": payload.conversion_mode,
                    "provider": refreshed.provider,
                },
            )
        except Exception as exc:
            _log.warning("Autovis usage tracking failed (non-blocking): %s", exc)

    return response
