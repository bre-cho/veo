from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RenderRebuildAuditLog(Base):
    """Persistent audit trail for approved rebuild execution events."""

    __tablename__ = "render_rebuild_audit_logs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    job_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    episode_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    changed_scene_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    selected_strategy: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    extras_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
        index=True,
    )
