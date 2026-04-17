from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TemplateGovernanceExecutionPlan(Base):
    __tablename__ = "template_governance_execution_plan"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    template_pack_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    bulk_operation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    execution_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    target_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TemplateGovernanceExecutionStep(Base):
    __tablename__ = "template_governance_execution_step"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("template_governance_execution_plan.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_key: Mapped[str] = mapped_column(String(128), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TemplateGovernancePlanTimelineEvent(Base):
    __tablename__ = "template_governance_plan_timeline_event"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("template_governance_execution_plan.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


Index("ix_template_governance_execution_plan_status", TemplateGovernanceExecutionPlan.status)
Index("ix_template_governance_execution_plan_created_at", TemplateGovernanceExecutionPlan.created_at)
Index("ix_template_governance_execution_step_plan_id", TemplateGovernanceExecutionStep.plan_id)
Index("ix_template_governance_execution_step_status", TemplateGovernanceExecutionStep.status)
Index("ix_template_governance_plan_timeline_event_plan_id", TemplateGovernancePlanTimelineEvent.plan_id)
Index("ix_template_governance_plan_timeline_event_event_type", TemplateGovernancePlanTimelineEvent.event_type)
Index("ix_template_governance_plan_timeline_event_created_at", TemplateGovernancePlanTimelineEvent.created_at)
