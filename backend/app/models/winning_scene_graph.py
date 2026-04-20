"""WinningSceneGraph DB model.

Phase 4.4: Table for persisting high-converting storyboard scene graphs.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, Float, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class WinningSceneGraph(Base):
    """Persisted scene graph snapshot for a high-converting storyboard.

    Only stored when ``conversion_score >= _SCORE_THRESHOLD_HIGH`` (0.70).
    Used by StoryboardEngine.generate_from_script() when ``use_winning_graph=True``.
    """

    __tablename__ = "winning_scene_graphs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    storyboard_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    platform: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    conversion_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    # Ordered list of {scene_goal, pacing_weight, visual_type} dicts
    scene_sequence: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    # Scene dependency graph snapshot
    dependency_graph: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    recorded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True, default=_now, index=True
    )
