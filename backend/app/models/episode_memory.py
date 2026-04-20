from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EpisodeMemory(Base):
    """Cross-episode narrative memory for the Director OS (Storyboard Engine).

    Each row records the state of a single episode within a series.
    ``open_loops`` holds unresolved narrative threads; ``resolved_loops``
    records which threads were closed in this episode.  The StoryboardEngine
    reads the most recent row when generating the next episode so open loops
    can be auto-injected as resolution beats.
    """

    __tablename__ = "episode_memories"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    series_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    episode_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # Freeform JSON: avatar state, colour palette, product state, etc.
    character_state: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    # List[str] — open narrative threads at the end of this episode
    open_loops: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    # List[str] — threads closed during this episode
    resolved_loops: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    storyboard_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_now, index=True
    )
