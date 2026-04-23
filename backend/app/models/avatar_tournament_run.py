"""avatar_tournament_run — records a single avatar selection tournament run."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AvatarTournamentRun(Base):
    """One tournament run per selection event.

    Tracks the context and outcome of each time the system chose an avatar
    for a given project/topic/template context.
    """

    __tablename__ = "avatar_tournament_run"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    workspace_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    topic_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    template_family: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    platform: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="completed", index=True
    )  # pending|running|completed|cancelled
    selection_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="exploit"
    )  # exploit|explore|forced_test
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, onupdate=_now
    )
