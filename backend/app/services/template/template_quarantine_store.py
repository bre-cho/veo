"""template_quarantine_store — manages the quarantine state of templates.

Quarantined templates:
- cannot enter the selector
- cannot participate in the tournament
- cannot be used as parents for evolution
- can only be debug-tested offline

The store is backed by a simple in-memory dict and is intentionally
stateless across restarts.  Production deployments can swap this for a
Redis or DB-backed store by subclassing or replacing.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_QUARANTINE_REGISTRY: dict[str, dict[str, Any]] = {}


class TemplateQuarantineStore:
    """Thread-safe (GIL) in-process quarantine registry."""

    def quarantine(
        self,
        *,
        template_id: str,
        reason: str,
        severity: str = "soft",
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add a template to quarantine.

        Parameters
        ----------
        template_id:
            ID of the template to quarantine.
        reason:
            Human-readable reason (e.g. "retention_collapse", "policy_violation").
        severity:
            ``"soft"`` (revivable) or ``"hard"`` (permanent).
        extra:
            Optional extra context stored alongside the record.

        Returns
        -------
        The quarantine record.
        """
        record: dict[str, Any] = {
            "template_id": template_id,
            "reason": reason,
            "severity": severity,
            "quarantined_at": datetime.now(timezone.utc).isoformat(),
        }
        if extra:
            record["extra"] = extra

        _QUARANTINE_REGISTRY[template_id] = record
        logger.warning(
            "Template quarantined | template_id=%s reason=%s severity=%s",
            template_id,
            reason,
            severity,
        )
        return record

    def release(self, template_id: str) -> bool:
        """Remove a template from quarantine (soft-release only).

        Returns True if the template was in quarantine and was removed.
        """
        record = _QUARANTINE_REGISTRY.get(template_id)
        if record is None:
            return False
        if record.get("severity") == "hard":
            logger.warning(
                "Attempted to release hard-quarantined template %s — ignored.",
                template_id,
            )
            return False
        del _QUARANTINE_REGISTRY[template_id]
        logger.info("Template released from quarantine | template_id=%s", template_id)
        return True

    def is_quarantined(self, template_id: str) -> bool:
        """Return True when the template is currently in quarantine."""
        return template_id in _QUARANTINE_REGISTRY

    def get_record(self, template_id: str) -> dict[str, Any] | None:
        """Return the quarantine record for a template or None."""
        return _QUARANTINE_REGISTRY.get(template_id)

    def list_quarantined(self) -> list[dict[str, Any]]:
        """Return all currently quarantined template records."""
        return list(_QUARANTINE_REGISTRY.values())

    def clear(self) -> None:
        """Flush the quarantine store (useful in tests)."""
        _QUARANTINE_REGISTRY.clear()
