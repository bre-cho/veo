"""avatar_scorecard — computes a structured performance score for an avatar run.

Score composition
-----------------
retention_score    = 0.70 × retention_30s + 0.30 × avg_watch_ratio
engagement_score   = 0.40 × like_rate + 0.30 × comment_rate + 0.30 × share_rate
series_follow_score = series_continue_rate

total_score        = 0.40 × retention + 0.30 × engagement + 0.30 × series_follow

All input metrics are assumed to be floats in [0, 1].
total_score is in [0, 1].
"""
from __future__ import annotations

from app.schemas.avatar_system import AvatarPerformanceScore


class AvatarScorecard:
    """Computes a composite performance score for an avatar from publish metrics."""

    def compute(
        self,
        *,
        avatar_id: str,
        market_code: str | None,
        content_goal: str | None,
        topic_class: str | None,
        metrics: dict,
    ) -> AvatarPerformanceScore:
        """Compute the avatar's performance score from raw publish metrics.

        Parameters
        ----------
        avatar_id:
            The avatar being scored.
        market_code / content_goal / topic_class:
            Context identifiers stored alongside the score for later lookup.
        metrics:
            Dict with keys: retention_30s, avg_watch_ratio, like_rate,
            comment_rate, share_rate, series_continue_rate.
            Missing keys default to 0.0.
        """
        retention_score = (
            0.70 * float(metrics.get("retention_30s", 0.0))
            + 0.30 * float(metrics.get("avg_watch_ratio", 0.0))
        )
        engagement_score = (
            0.40 * float(metrics.get("like_rate", 0.0))
            + 0.30 * float(metrics.get("comment_rate", 0.0))
            + 0.30 * float(metrics.get("share_rate", 0.0))
        )
        series_follow_score = float(metrics.get("series_continue_rate", 0.0))

        total_score = (
            0.40 * retention_score
            + 0.30 * engagement_score
            + 0.30 * series_follow_score
        )

        return AvatarPerformanceScore(
            avatar_id=avatar_id,
            market_code=market_code,
            content_goal=content_goal,
            topic_class=topic_class,
            retention_score=round(retention_score, 4),
            engagement_score=round(engagement_score, 4),
            series_follow_score=round(series_follow_score, 4),
            total_score=round(total_score, 4),
        )
