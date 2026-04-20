from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PublishJob(Base):
    __tablename__ = "publish_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    channel_plan_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    platform: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    publish_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="SIMULATED", index=True)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    request_payload: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    provider_response: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    external_ids: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    error_log: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    retry_metadata: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parent_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    payload: Mapped[Any] = mapped_column(JSON, nullable=False)
    signal_status: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    # Idempotency key = sha256(platform + channel_plan_id + payload_hash).
    # Used to prevent duplicate publishes for the same content.
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    # Preflight validation status: null (not run) | "ok" | "error"
    preflight_status: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    preflight_errors: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    # Phase 3.1: per-platform final state metadata (monetization, review status, etc.)
    provider_metadata: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    preparing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    publishing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
        index=True,
    )
