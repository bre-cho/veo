"""factory_metrics – metric emission helpers for the factory pipeline.

Stage adapters call ``emit_metric`` to record numeric observations.  The
FactoryOrchestrator reads aggregated metrics via ``get_run_metrics``.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.factory_run import FactoryMetricEvent

logger = logging.getLogger(__name__)


def emit_metric(
    db: Session,
    run_id: str,
    stage_name: str,
    metric_name: str,
    metric_value: float | int | str,
    unit: str | None = None,
) -> None:
    """Write a single metric observation."""
    now = datetime.now(timezone.utc)
    event = FactoryMetricEvent(
        run_id=run_id,
        stage_name=stage_name,
        metric_name=metric_name,
        metric_value=str(metric_value),
        unit=unit,
        recorded_at=now,
    )
    db.add(event)
    db.commit()
    logger.debug(
        "Metric emitted: run=%s stage=%s %s=%s %s",
        run_id, stage_name, metric_name, metric_value, unit or "",
    )


def get_run_metrics(db: Session, run_id: str) -> list[dict]:
    """Return all metric events for a run as plain dicts."""
    rows = (
        db.query(FactoryMetricEvent)
        .filter(FactoryMetricEvent.run_id == run_id)
        .order_by(FactoryMetricEvent.recorded_at)
        .all()
    )
    return [
        {
            "id": r.id,
            "stage_name": r.stage_name,
            "metric_name": r.metric_name,
            "metric_value": r.metric_value,
            "unit": r.unit,
            "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
        }
        for r in rows
    ]
