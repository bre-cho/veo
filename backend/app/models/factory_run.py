"""SQLAlchemy models for the Factory Orchestrator pipeline.

Tables
------
factory_runs             – top-level pipeline execution record
factory_run_stages       – per-stage trace for each run
factory_quality_gates    – quality gate evaluation events
factory_memory_events    – DNA / learning memory blobs
factory_metric_events    – numeric metrics emitted by any stage
factory_incidents        – anomalies / blocking events during a run
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class FactoryRun(Base):
    """Top-level record for a single closed-loop factory execution."""

    __tablename__ = "factory_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    trace_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # Input
    input_type: Mapped[str] = mapped_column(String(32), default="topic")  # topic|script|avatar|series
    input_topic: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    input_script: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    input_avatar_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    input_series_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # State machine
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    current_stage: Mapped[str] = mapped_column(String(64), default="INTAKE", index=True)
    percent_complete: Mapped[int] = mapped_column(Integer, default=0)

    # Output links
    render_job_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    output_video_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_thumbnail_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    seo_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    seo_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    publish_payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Blocking / error
    blocking_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Budget / policy
    budget_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    policy_mode: Mapped[str] = mapped_column(String(32), default="production")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                   default=lambda: datetime.utcnow())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class FactoryRunStage(Base):
    """Per-stage execution trace for a FactoryRun."""

    __tablename__ = "factory_run_stages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    stage_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    stage_index: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|running|done|failed|skipped
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    input_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)


class FactoryQualityGate(Base):
    """Quality gate evaluation recorded during a factory run."""

    __tablename__ = "factory_quality_gates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    stage_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    gate_name: Mapped[str] = mapped_column(String(64), nullable=False)

    result: Mapped[str] = mapped_column(String(32), nullable=False)  # pass|fail|warn|skip
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    threshold: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    action_taken: Mapped[str] = mapped_column(String(32), default="none")  # none|block|retry|downgrade|human_review
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                     default=lambda: datetime.utcnow())


class FactoryMemoryEvent(Base):
    """DNA / learning memory blob emitted after each run or stage."""

    __tablename__ = "factory_memory_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    memory_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # topic_dna | script_dna | scene_dna | avatar_dna | render_dna | seo_dna |
    # performance_dna | failure_dna | winner_dna
    payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                    default=lambda: datetime.utcnow())


class FactoryMetricEvent(Base):
    """Numeric metric emitted by any stage of the factory pipeline."""

    __tablename__ = "factory_metric_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    stage_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False)
    metric_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                    default=lambda: datetime.utcnow())


class FactoryIncident(Base):
    """Anomaly or blocking event raised during a factory run."""

    __tablename__ = "factory_incidents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    stage_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    severity: Mapped[str] = mapped_column(String(32), default="error")  # info|warn|error|critical
    incident_type: Mapped[str] = mapped_column(String(64), nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(default=False)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                    default=lambda: datetime.utcnow())
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
