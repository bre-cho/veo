from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass
class DramaMetricEvent:
    metric_name: str
    metric_value: float
    scene_id: Optional[str] = None
    episode_id: Optional[str] = None
    project_id: Optional[str] = None
    tags: Optional[Dict[str, str]] = None


class DramaMetrics:
    """Thin metrics facade.

    Replace internals with Prometheus / StatsD / OpenTelemetry when wiring into
    the host monorepo. API is kept stable for workers and services.
    """

    def increment(self, metric_name: str, value: float = 1.0, **context: Any) -> Dict[str, Any]:
        event = DramaMetricEvent(metric_name=metric_name, metric_value=value, **self._clean_context(context))
        return asdict(event)

    def gauge(self, metric_name: str, value: float, **context: Any) -> Dict[str, Any]:
        event = DramaMetricEvent(metric_name=metric_name, metric_value=value, **self._clean_context(context))
        return asdict(event)

    def timing_ms(self, metric_name: str, value: float, **context: Any) -> Dict[str, Any]:
        event = DramaMetricEvent(metric_name=metric_name, metric_value=value, **self._clean_context(context))
        return asdict(event)

    def _clean_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        allowed = {"scene_id", "episode_id", "project_id", "tags"}
        return {key: value for key, value in context.items() if key in allowed}
