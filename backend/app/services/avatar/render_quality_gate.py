"""RenderQualityGate — composite quality scoring for render output."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PUBLISH_QUALITY_THRESHOLD = 0.75

# Weights for composite quality score
_IDENTITY_WEIGHT = 0.50
_TEMPORAL_WEIGHT = 0.35
_RESOLUTION_WEIGHT = 0.15


@dataclass
class QualityReport:
    """Composite quality report for a render output.

    ``passed`` is True when ``composite_score >= PUBLISH_QUALITY_THRESHOLD``.
    """

    identity_score: float
    temporal_score: float
    resolution_score: float = 1.0
    composite_score: float = field(init=False)
    passed: bool = field(init=False)
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.composite_score = round(
            self.identity_score * _IDENTITY_WEIGHT
            + self.temporal_score * _TEMPORAL_WEIGHT
            + self.resolution_score * _RESOLUTION_WEIGHT,
            3,
        )
        self.passed = self.composite_score >= PUBLISH_QUALITY_THRESHOLD


class RenderQualityGate:
    """Evaluate render output quality against the publish threshold.

    Usage::

        gate = RenderQualityGate()
        report = gate.evaluate(identity_score=0.92, temporal_score=0.88)
        if not report.passed:
            ...
    """

    def evaluate(
        self,
        identity_score: float,
        temporal_score: float,
        resolution_score: float = 1.0,
    ) -> QualityReport:
        """Compute a composite quality score and return a ``QualityReport``."""
        return QualityReport(
            identity_score=float(identity_score),
            temporal_score=float(temporal_score),
            resolution_score=float(resolution_score),
        )
