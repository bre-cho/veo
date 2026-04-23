"""avatar_scorecard — computes a structured performance score for an avatar run.

Score composition
-----------------
retention_score    = 0.70 × retention_30s + 0.30 × avg_watch_ratio
engagement_score   = 0.40 × like_rate + 0.30 × comment_rate + 0.30 × share_rate
series_follow_score = series_continue_rate

total_score        = 0.40 × retention + 0.30 × engagement + 0.30 × series_follow

All input metrics are assumed to be floats in [0, 1].
total_score is in [0, 1].

fitness_score (tournament layer)
---------------------------------
0.25 × normalized_ctr
+ 0.35 × normalized_retention
+ 0.15 × normalized_watch_time
+ 0.15 × normalized_conversion
+ 0.10 × normalized_continuity_health
"""
from __future__ import annotations

from typing import Any

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

    def compute_fitness_score(
        self,
        *,
        metrics: dict[str, Any],
        continuity_health: float = 0.5,
    ) -> float:
        """Compute a tournament-ready fitness score from publish metrics.

        Fitness score formula (phase 1):
            0.25 × ctr
          + 0.35 × retention_30s
          + 0.15 × avg_watch_ratio
          + 0.15 × conversion_rate
          + 0.10 × continuity_health

        All inputs are floats in [0, 1].
        """
        ctr = float(metrics.get("ctr", 0.0))
        retention = float(metrics.get("retention_30s", 0.0))
        watch_time = float(metrics.get("avg_watch_ratio", 0.0))
        conversion = float(metrics.get("conversion_rate", 0.0))

        fitness = (
            0.25 * ctr
            + 0.35 * retention
            + 0.15 * watch_time
            + 0.15 * conversion
            + 0.10 * max(0.0, min(1.0, continuity_health))
        )
        return round(fitness, 4)

    def build_avatar_scorecard(
        self,
        *,
        avatar_id: str,
        market_code: str | None,
        content_goal: str | None,
        topic_class: str | None,
        metrics: dict[str, Any],
        continuity_health: float = 0.5,
    ) -> dict[str, Any]:
        """Build a full tournament-ready scorecard payload.

        Combines the performance score with predicted tournament signals.
        """
        perf = self.compute(
            avatar_id=avatar_id,
            market_code=market_code,
            content_goal=content_goal,
            topic_class=topic_class,
            metrics=metrics,
        )
        fitness = self.compute_fitness_score(
            metrics=metrics,
            continuity_health=continuity_health,
        )
        return {
            "avatar_id": avatar_id,
            "predicted_score": perf.total_score,
            "predicted_ctr": float(metrics.get("ctr", 0.0)),
            "predicted_retention": perf.retention_score,
            "predicted_conversion": float(metrics.get("conversion_rate", 0.0)),
            "brand_fit_score": perf.engagement_score,
            "continuity_score": continuity_health,
            "fitness_score": fitness,
            "pair_fit_score": None,
        }
