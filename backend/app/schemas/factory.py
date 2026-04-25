"""Pydantic schemas for the Factory pipeline API."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class FactoryRunRequest(BaseModel):
    input_type: str = Field("topic", description="topic | script | avatar | series")
    input_topic: Optional[str] = None
    input_script: Optional[str] = None
    input_avatar_id: Optional[str] = None
    input_series_id: Optional[str] = None
    project_id: Optional[str] = None
    budget_cents: Optional[int] = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class StageOut(BaseModel):
    id: str
    run_id: str
    stage_name: str
    stage_index: int
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    error_detail: Optional[str] = None
    retry_count: int = 0

    model_config = {"from_attributes": True}


class QualityGateOut(BaseModel):
    id: str
    run_id: str
    stage_name: str
    gate_name: str
    result: str
    score: Optional[int] = None
    threshold: Optional[int] = None
    action_taken: str
    detail: Optional[str] = None
    evaluated_at: datetime

    model_config = {"from_attributes": True}


class IncidentOut(BaseModel):
    id: str
    run_id: str
    stage_name: Optional[str] = None
    severity: str
    incident_type: str
    detail: Optional[str] = None
    resolved: bool
    occurred_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MetricOut(BaseModel):
    id: str
    run_id: str
    stage_name: str
    metric_name: str
    metric_value: Optional[str] = None
    unit: Optional[str] = None
    recorded_at: datetime

    model_config = {"from_attributes": True}


class MemoryEventOut(BaseModel):
    id: str
    run_id: str
    memory_type: str
    payload_json: Optional[str] = None
    recorded_at: datetime

    model_config = {"from_attributes": True}


class FactoryRunOut(BaseModel):
    id: str
    trace_id: Optional[str] = None
    project_id: Optional[str] = None
    input_type: str
    input_topic: Optional[str] = None
    status: str
    current_stage: str
    percent_complete: int
    render_job_id: Optional[str] = None
    output_video_url: Optional[str] = None
    output_thumbnail_url: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    blocking_reason: Optional[str] = None
    error_detail: Optional[str] = None
    policy_mode: str
    budget_cents: Optional[int] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class FactoryRunDetailOut(FactoryRunOut):
    stages: list[StageOut] = []
    quality_gates: list[QualityGateOut] = []
    incidents: list[IncidentOut] = []


class TimelineOut(BaseModel):
    run_id: str
    stages: list[StageOut]


class MetricsOut(BaseModel):
    run_id: str
    metrics: list[MetricOut]
