"""template_incident_logger — lightweight in-process incident registry.

Each incident record captures:
- template_id
- failure_type  (e.g. "retention_crash", "runtime_error", "policy_violation")
- metrics snapshot at time of failure
- ISO-8601 timestamp
- action_taken  (e.g. "rollback", "quarantine", "rate_limit")

Records are kept in memory and can optionally be persisted to a DB when a
session is provided.  The logger is intentionally non-fatal: it never raises.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_INCIDENT_BUFFER: list[dict[str, Any]] = []
_MAX_BUFFER = 500


class TemplateIncidentLogger:
    """Append-only incident log for template governance failures."""

    def log_incident(
        self,
        *,
        template_id: str,
        failure_type: str,
        metrics: dict[str, Any] | None = None,
        action_taken: str = "rollback",
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create and store an incident record.

        Parameters
        ----------
        template_id:
            The template that triggered the incident.
        failure_type:
            Short label for the failure category.
        metrics:
            Snapshot of the metrics at the time of the failure.
        action_taken:
            The action taken in response (rollback / quarantine / rate_limit).
        extra:
            Any additional context dict.

        Returns
        -------
        The incident record dict.
        """
        record: dict[str, Any] = {
            "template_id": template_id,
            "failure_type": failure_type,
            "metrics": metrics or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action_taken": action_taken,
        }
        if extra:
            record["extra"] = extra

        try:
            if len(_INCIDENT_BUFFER) >= _MAX_BUFFER:
                _INCIDENT_BUFFER.pop(0)
            _INCIDENT_BUFFER.append(record)
        except Exception:
            pass

        logger.warning(
            "Template incident logged | template_id=%s failure=%s action=%s",
            template_id,
            failure_type,
            action_taken,
        )
        return record

    def get_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the most recent *limit* incident records (newest first)."""
        return list(reversed(_INCIDENT_BUFFER[-limit:]))

    def get_for_template(self, template_id: str) -> list[dict[str, Any]]:
        """Return all incidents recorded for a specific template."""
        return [r for r in _INCIDENT_BUFFER if r.get("template_id") == template_id]

    def clear(self) -> None:
        """Flush the in-memory buffer (useful in tests)."""
        _INCIDENT_BUFFER.clear()
