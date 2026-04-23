"""anomaly_detector — detects metric anomalies relative to a context baseline."""
from __future__ import annotations

from typing import Any

from app.schemas.avatar_healing import AvatarAnomalyReport


class AvatarAnomalyDetector:
    """Compares incoming metrics against an optional baseline and returns an
    :class:`AvatarAnomalyReport`.

    Thresholds
    ----------
    - ``retention_crash``: retention < 0.30 (absolute floor)
    - ``ctr_drop``: ctr < 0.04 (absolute floor)
    - ``continuity_break``: continuity_health < 0.60
    - Relative drops vs baseline: retention < 60% of baseline, ctr < 50% of baseline
    """

    # Absolute floors
    RETENTION_FLOOR: float = 0.30
    CTR_FLOOR: float = 0.04
    CONTINUITY_FLOOR: float = 0.60

    # Relative drop thresholds (as fraction of baseline)
    RETENTION_DROP_RATIO: float = 0.60
    CTR_DROP_RATIO: float = 0.50

    def detect(
        self,
        metrics: dict[str, Any],
        baseline: dict[str, Any] | None = None,
    ) -> AvatarAnomalyReport:
        """Return an :class:`AvatarAnomalyReport` describing detected anomalies.

        Parameters
        ----------
        metrics:
            Post-publish metric dict.  Recognised keys: ``retention``,
            ``retention_30s``, ``ctr``, ``continuity_health``.
        baseline:
            Optional baseline dict with ``retention_ewma`` and ``ctr_ewma``
            keys.  When provided, relative-drop detection is enabled.
        """
        baseline = baseline or {}
        retention = float(
            metrics.get("retention") or metrics.get("retention_30s") or 0.0
        )
        ctr = float(metrics.get("ctr") or 0.0)
        continuity_health = float(metrics.get("continuity_health") or 1.0)
        baseline_retention = float(baseline.get("retention_ewma") or retention)
        baseline_ctr = float(baseline.get("ctr_ewma") or ctr)

        anomaly_type: str | None = None
        severity: str = "none"

        # Priority: check continuity break first (structural issue)
        if continuity_health < self.CONTINUITY_FLOOR:
            anomaly_type = "continuity_break"
            severity = "medium"
        # Absolute floor checks
        elif retention < self.RETENTION_FLOOR:
            anomaly_type = "retention_drop"
            severity = "critical" if retention < 0.15 else "high"
        elif ctr < self.CTR_FLOOR:
            anomaly_type = "ctr_drop"
            severity = "high" if ctr < 0.02 else "medium"
        # Relative drop checks (only when baseline has meaningful data)
        elif baseline_retention > 0 and retention < baseline_retention * self.RETENTION_DROP_RATIO:
            anomaly_type = "retention_drop"
            severity = "medium"
        elif baseline_ctr > 0 and ctr < baseline_ctr * self.CTR_DROP_RATIO:
            anomaly_type = "ctr_drop"
            severity = "low"

        return AvatarAnomalyReport(
            has_anomaly=anomaly_type is not None,
            anomaly_type=anomaly_type,
            severity=severity,
            retention=retention,
            ctr=ctr,
            continuity_health=continuity_health,
            baseline_retention=baseline_retention if baseline else None,
            baseline_ctr=baseline_ctr if baseline else None,
        )
