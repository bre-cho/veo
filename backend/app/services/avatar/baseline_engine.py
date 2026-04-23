"""baseline_engine — updates and retrieves EWMA performance baselines per context."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.avatar_context_baseline import AvatarContextBaseline
from app.schemas.avatar_learning import BaselineSnapshot

_ALPHA = 0.2  # EWMA smoothing factor


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class BaselineEngine:
    """Maintains an exponentially-weighted moving average (EWMA) of performance
    metrics for each (topic_signature, template_family, platform) context.

    The baseline is used to:
    - Detect relative performance drops (anomaly detection)
    - Normalise rewards for the bandit engine
    - Provide dynamic thresholds for governance rules
    """

    def __init__(self, alpha: float = _ALPHA) -> None:
        self._alpha = alpha

    def update(
        self,
        db: Session,
        *,
        context: dict[str, Any],
        metrics: dict[str, Any],
    ) -> BaselineSnapshot:
        """Update the EWMA baseline for *context* with the new *metrics* and
        return a :class:`BaselineSnapshot`.
        """
        row = self._get_or_create(db, context=context)

        def ewma(old: float, new: float) -> float:
            return old * (1 - self._alpha) + new * self._alpha

        row.ctr_ewma = ewma(row.ctr_ewma, float(metrics.get("ctr") or 0.0))
        row.retention_ewma = ewma(
            row.retention_ewma,
            float(metrics.get("retention") or metrics.get("retention_30s") or 0.0),
        )
        row.watch_time_ewma = ewma(
            row.watch_time_ewma, float(metrics.get("watch_time") or 0.0)
        )
        row.conversion_ewma = ewma(
            row.conversion_ewma, float(metrics.get("conversion") or 0.0)
        )
        row.sample_count += 1
        row.updated_at = _now()

        db.commit()
        return self._to_snapshot(row)

    def get(
        self,
        db: Session,
        *,
        context: dict[str, Any],
    ) -> BaselineSnapshot | None:
        """Return the current baseline snapshot for *context*, or ``None`` if
        no baseline exists yet.
        """
        row = (
            db.query(AvatarContextBaseline)
            .filter(
                AvatarContextBaseline.topic_signature == context.get("topic_signature"),
                AvatarContextBaseline.template_family == context.get("template_family"),
                AvatarContextBaseline.platform == context.get("platform"),
            )
            .one_or_none()
        )
        if row is None:
            return None
        return self._to_snapshot(row)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_or_create(self, db: Session, *, context: dict[str, Any]) -> AvatarContextBaseline:
        row = (
            db.query(AvatarContextBaseline)
            .filter(
                AvatarContextBaseline.topic_signature == context.get("topic_signature"),
                AvatarContextBaseline.template_family == context.get("template_family"),
                AvatarContextBaseline.platform == context.get("platform"),
            )
            .one_or_none()
        )
        if row is None:
            row = AvatarContextBaseline(
                topic_signature=context.get("topic_signature"),
                template_family=context.get("template_family"),
                platform=context.get("platform"),
            )
            db.add(row)
            db.commit()
        return row

    @staticmethod
    def _to_snapshot(row: AvatarContextBaseline) -> BaselineSnapshot:
        return BaselineSnapshot(
            topic_signature=row.topic_signature,
            template_family=row.template_family,
            platform=row.platform,
            ctr_ewma=row.ctr_ewma,
            retention_ewma=row.retention_ewma,
            watch_time_ewma=row.watch_time_ewma,
            conversion_ewma=row.conversion_ewma,
            sample_count=row.sample_count,
        )
