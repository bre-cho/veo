"""Pydantic schemas for ML recommendation API."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TrainRequest(BaseModel):
    lookback_days: int = Field(default=30, ge=1, le=365)
    min_samples: int = Field(default=10, ge=1)


class TrainResponse(BaseModel):
    ok: bool
    samples: int = 0
    loss_fail: float | None = None
    loss_slow: float | None = None
    reason: str | None = None


class PredictRequest(BaseModel):
    features: dict[str, Any] = Field(
        ...,
        description="Map of feature name → value. "
        "Known features: planned_scene_count, provider_veo, provider_runway, "
        "provider_kling, provider_other, hour_of_day, day_of_week.",
    )
    job_id: str | None = Field(default=None)


class PredictResponse(BaseModel):
    fail_risk: float
    slow_render: float
    is_trained: bool
    recommendation: str | None = None
    job_id: str | None = None


class FeatureSummaryResponse(BaseModel):
    stats: dict[str, Any]
    sample_count: int
