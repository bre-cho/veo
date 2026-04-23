"""avatar_memory_service — retrieves historical avatar performance from the DB.

Used during avatar selection to boost avatars that have demonstrated strong
performance in the same context (market × goal × topic).

Falls back gracefully when no DB session is available or when no historical
rows exist.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.avatar_performance import AvatarPerformance


class AvatarMemoryService:
    """Read-only access to avatar performance history."""

    def get_recent_avatar_score(
        self,
        db: Session | None,
        *,
        avatar_id: str,
        market_code: str | None = None,
        content_goal: str | None = None,
        topic_class: str | None = None,
    ) -> dict[str, Any]:
        """Return the most recent performance record for the given context.

        Parameters
        ----------
        db:
            Active SQLAlchemy session.  If ``None``, returns an empty dict.
        avatar_id:
            Avatar whose history to look up.
        market_code / content_goal / topic_class:
            Optional context filters.  Each ``None`` parameter is ignored
            (i.e. all records for that dimension are included).

        Returns
        -------
        A dict with keys: avatar_id, retention_score, engagement_score,
        series_follow_score, total_score, template_id, metrics.
        Returns an empty dict when no records are found.
        """
        if db is None:
            return {}

        try:
            query = db.query(AvatarPerformance).filter(
                AvatarPerformance.avatar_id == avatar_id
            )
            if market_code is not None:
                query = query.filter(AvatarPerformance.market_code == market_code)
            if content_goal is not None:
                query = query.filter(AvatarPerformance.content_goal == content_goal)
            if topic_class is not None:
                query = query.filter(AvatarPerformance.topic_class == topic_class)

            row = query.order_by(AvatarPerformance.created_at.desc()).first()
        except Exception:
            return {}

        if row is None:
            return {}

        return {
            "avatar_id": row.avatar_id,
            "retention_score": row.retention_score,
            "engagement_score": row.engagement_score,
            "series_follow_score": row.series_follow_score,
            "total_score": row.total_score,
            "template_id": row.template_id,
            "metrics": row.metrics or {},
        }

    def save_performance(
        self,
        db: Session,
        *,
        avatar_id: str,
        market_code: str | None,
        content_goal: str | None,
        topic_class: str | None,
        template_id: str | None,
        retention_score: float,
        engagement_score: float,
        series_follow_score: float,
        total_score: float,
        metrics: dict[str, Any] | None = None,
    ) -> AvatarPerformance:
        """Persist a new performance record to the database."""
        record = AvatarPerformance(
            avatar_id=avatar_id,
            market_code=market_code,
            content_goal=content_goal,
            topic_class=topic_class,
            template_id=template_id,
            retention_score=retention_score,
            engagement_score=engagement_score,
            series_follow_score=series_follow_score,
            total_score=total_score,
            metrics=metrics or {},
        )
        db.add(record)
        db.flush()
        return record
