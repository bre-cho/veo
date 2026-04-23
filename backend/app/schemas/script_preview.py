from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


AspectRatio = Literal["9:16", "16:9", "1:1"]
SourceMode = Literal["script_upload", "topic_intake"]
TargetPlatform = Literal["shorts", "tiktok", "reels", "youtube"]


class ScriptScene(BaseModel):
    scene_index: int = Field(..., ge=1)
    title: str
    script_text: str
    visual_prompt: str | None = None
    shot_hint: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    target_duration_sec: float = Field(..., gt=0)

    @field_validator("title", "script_text")
    @classmethod
    def validate_non_empty_text(cls, value: str):
        value = value.strip()
        if not value:
            raise ValueError("Field cannot be empty")
        return value


class SubtitleSegment(BaseModel):
    scene_index: int | None = Field(default=None, ge=1)
    text: str
    start_sec: float = Field(..., ge=0)
    end_sec: float = Field(..., gt=0)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str):
        value = value.strip()
        if not value:
            raise ValueError("Subtitle text cannot be empty")
        return value

    @model_validator(mode="after")
    def validate_timing(self):
        if self.end_sec <= self.start_sec:
            raise ValueError("end_sec must be greater than start_sec")
        return self


class ScriptPreviewPayload(BaseModel):
    avatar_id: str | None = None
    market_code: str | None = None
    content_goal: str | None = None
    conversion_mode: str | None = None
    source_mode: SourceMode = "script_upload"
    aspect_ratio: AspectRatio
    target_platform: TargetPlatform
    style_preset: str | None = None
    original_filename: str | None = None
    script_text: str
    scenes: list[ScriptScene]
    subtitle_segments: list[SubtitleSegment]
    storyboard: dict[str, Any] | None = None
    optimization_response: dict[str, Any] | None = None
    winner_patterns: list[dict[str, Any]] | None = None
    # Brain Layer enrichment fields (optional, backward-compatible)
    series_id: str | None = None
    episode_index: int | None = None
    brain_plan: dict[str, Any] | None = None
    continuity_context: dict[str, Any] | None = None
    winner_dna_summary: dict[str, Any] | None = None
    memory_refs: dict[str, Any] | None = None

    @field_validator("script_text")
    @classmethod
    def validate_script_text(cls, value: str):
        value = value.strip()
        if not value:
            raise ValueError("script_text is required")
        return value

    @field_validator("scenes")
    @classmethod
    def validate_scenes_not_empty(cls, value: list[ScriptScene]):
        if not value:
            raise ValueError("At least one scene is required")
        return value

    @field_validator("subtitle_segments")
    @classmethod
    def validate_subtitles_not_empty(cls, value: list[SubtitleSegment]):
        if not value:
            raise ValueError("At least one subtitle segment is required")
        return value

    @model_validator(mode="after")
    def validate_scene_indexes(self):
        expected = list(range(1, len(self.scenes) + 1))
        actual = [scene.scene_index for scene in self.scenes]
        if actual != expected:
            raise ValueError("Scene indexes must be sequential starting from 1")
        return self


class ConfirmCreateProjectRequest(BaseModel):
    name: str
    idea: str | None = None
    preview_payload: ScriptPreviewPayload
    confirmed: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str):
        value = value.strip()
        if not value:
            raise ValueError("name is required")
        return value
