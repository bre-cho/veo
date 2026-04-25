"""Exactly-Once Approved Rebuild Executor.

Consumes a decision payload that has been *approved* by an operator or the
automated pipeline and executes the rebuild exactly once, using an idempotency
key to guard against duplicate submissions.

State machine::

    queued → approved → executing → succeeded
    queued → approved → executing → failed → incident_required
    queued → blocked
    queued → downgraded

Audit trail entries are appended to an in-process list (pluggable in
production via the ``audit_store`` constructor argument).
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------

STATUS_QUEUED = "queued"
STATUS_APPROVED = "approved"
STATUS_EXECUTING = "executing"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"
STATUS_INCIDENT_REQUIRED = "incident_required"
STATUS_BLOCKED = "blocked"
STATUS_DOWNGRADED = "downgraded"


# ---------------------------------------------------------------------------
# Default in-memory audit store (replaced in production by a real backend)
# ---------------------------------------------------------------------------

_DEFAULT_AUDIT_LOG: List[Dict[str, Any]] = []


def _default_append_audit(entry: Dict[str, Any]) -> None:
    _DEFAULT_AUDIT_LOG.append(entry)


def get_default_audit_log() -> List[Dict[str, Any]]:
    """Return the in-memory audit log (testing / single-process use only)."""
    return list(_DEFAULT_AUDIT_LOG)


def clear_default_audit_log() -> None:
    """Clear the in-memory audit log (testing only)."""
    _DEFAULT_AUDIT_LOG.clear()


# ---------------------------------------------------------------------------
# Idempotency registry (in-memory; replace with Redis/DB in production)
# ---------------------------------------------------------------------------

_IDEMPOTENCY_REGISTRY: Dict[str, Dict[str, Any]] = {}


def _compute_idempotency_key(decision: Dict[str, Any]) -> str:
    """Derive a stable idempotency key from the decision payload.

    The key is the SHA-256 of the JSON-serialised subset of deterministic
    decision fields so that re-submitting the same logical operation is
    detected and de-duped.
    """
    fingerprint = {
        "project_id": decision.get("project_id"),
        "episode_id": decision.get("episode_id"),
        "changed_scene_id": decision.get("changed_scene_id"),
        "change_type": decision.get("change_type"),
        "selected_strategy": decision.get("selected_strategy"),
        "rebuild_scene_ids": sorted(decision.get("rebuild_scene_ids") or []),
    }
    raw = json.dumps(fingerprint, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


class ApprovedRebuildExecutor:
    """Execute an approved rebuild decision exactly once.

    Args:
        rebuild_fn: Callable that performs the actual rebuild.  Must accept a
            dict with at minimum ``project_id``, ``episode_id``, and
            ``rebuild_scene_ids``; must return a result dict.  In production
            this wraps :class:`~app.render.reassembly.smart_reassembly_service.SmartReassemblyService`.
        status_updater: Optional callable ``(job_id, status, payload) → None``
            to propagate status changes to an external store (e.g. the DB).
        audit_store: Optional callable ``(entry) → None`` to persist audit
            entries.  Defaults to the in-memory log.
    """

    def __init__(
        self,
        rebuild_fn: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        status_updater: Optional[Callable[[str, str, Dict[str, Any]], None]] = None,
        audit_store: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self._rebuild_fn = rebuild_fn or self._noop_rebuild
        self._status_updater = status_updater
        self._audit_store = audit_store or _default_append_audit

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def execute(
        self,
        decision: Dict[str, Any],
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute the rebuild described by *decision*.

        Steps:
        1. Validate decision is approved (not blocked/downgraded).
        2. Derive idempotency key and reject duplicates.
        3. Revalidate scene/job status.
        4. Transition: approved → executing.
        5. Call rebuild function.
        6. Transition: executing → succeeded | failed → incident_required.
        7. Append audit trail entry.
        8. Return structured execution result.

        Args:
            decision: Output of
                :class:`~app.render.decision.unified_rebuild_decision_engine.UnifiedRebuildDecisionEngine.decide`.
            job_id: Optional caller-supplied job identifier.  One is generated
                from the idempotency key when omitted.

        Returns:
            Execution result dict (see ``_execution_result`` helper).
        """
        ikey = _compute_idempotency_key(decision)
        if job_id is None:
            job_id = ikey[:16]

        # ── Guard: blocked or downgraded decisions are not executable ──
        action = decision.get("decision", "block")
        if action == STATUS_BLOCKED:
            result = self._execution_result(
                job_id=job_id,
                status=STATUS_BLOCKED,
                decision=decision,
                message="Rebuild blocked by budget guard – no execution performed.",
            )
            self._record_audit(job_id=job_id, event="blocked", decision=decision)
            self._update_status(job_id, STATUS_BLOCKED, result)
            return result

        if action == STATUS_DOWNGRADED and not decision.get("rebuild_scene_ids"):
            result = self._execution_result(
                job_id=job_id,
                status=STATUS_DOWNGRADED,
                decision=decision,
                message="Strategy was downgraded but no scenes remain in scope.",
            )
            self._record_audit(job_id=job_id, event="downgraded_empty", decision=decision)
            self._update_status(job_id, STATUS_DOWNGRADED, result)
            return result

        # ── Guard: idempotency ──────────────────────────────────────
        if ikey in _IDEMPOTENCY_REGISTRY:
            previous = _IDEMPOTENCY_REGISTRY[ikey]
            _logger.info(
                "Idempotency hit for job %s (key=%s): returning previous result %s",
                job_id,
                ikey,
                previous.get("status"),
            )
            return previous

        # ── Transition: queued → approved ──────────────────────────
        self._record_audit(job_id=job_id, event=STATUS_APPROVED, decision=decision)
        self._update_status(
            job_id,
            STATUS_APPROVED,
            {"message": "Rebuild approved, execution starting."},
        )

        # ── Revalidate scene list ───────────────────────────────────
        rebuild_scene_ids: List[str] = decision.get("rebuild_scene_ids") or []
        if not rebuild_scene_ids:
            result = self._execution_result(
                job_id=job_id,
                status=STATUS_BLOCKED,
                decision=decision,
                message="No scenes in rebuild scope after revalidation.",
            )
            self._record_audit(job_id=job_id, event="blocked_empty_scenes", decision=decision)
            self._update_status(job_id, STATUS_BLOCKED, result)
            _IDEMPOTENCY_REGISTRY[ikey] = result
            return result

        # ── Transition: approved → executing ───────────────────────
        self._record_audit(job_id=job_id, event=STATUS_EXECUTING, decision=decision)
        self._update_status(
            job_id,
            STATUS_EXECUTING,
            {"rebuild_scene_ids": rebuild_scene_ids},
        )

        # ── Execute rebuild ─────────────────────────────────────────
        try:
            rebuild_payload = {
                "project_id": decision["project_id"],
                "episode_id": decision["episode_id"],
                "changed_scene_id": decision["changed_scene_id"],
                "change_type": decision.get("change_type", "subtitle"),
                "rebuild_scene_ids": rebuild_scene_ids,
                "selected_strategy": decision.get("selected_strategy"),
                "has_timeline_drift": decision.get("has_timeline_drift", False),
            }
            rebuild_result = self._rebuild_fn(rebuild_payload)
        except Exception as exc:  # noqa: BLE001
            _logger.exception("Rebuild execution failed for job %s", job_id)
            incident = self._build_incident_payload(
                job_id=job_id,
                decision=decision,
                error=exc,
            )
            result = self._execution_result(
                job_id=job_id,
                status=STATUS_INCIDENT_REQUIRED,
                decision=decision,
                message=f"Rebuild failed: {exc}",
                extras={"incident": incident},
            )
            self._record_audit(
                job_id=job_id,
                event=STATUS_INCIDENT_REQUIRED,
                decision=decision,
                extras={"error": str(exc), "incident": incident},
            )
            self._update_status(job_id, STATUS_INCIDENT_REQUIRED, result)
            _IDEMPOTENCY_REGISTRY[ikey] = result
            return result

        # ── Transition: executing → succeeded ──────────────────────
        result = self._execution_result(
            job_id=job_id,
            status=STATUS_SUCCEEDED,
            decision=decision,
            message="Rebuild completed successfully.",
            extras={"rebuild_result": rebuild_result},
        )
        self._record_audit(
            job_id=job_id,
            event=STATUS_SUCCEEDED,
            decision=decision,
            extras={"rebuild_result_status": rebuild_result.get("status")},
        )
        self._update_status(job_id, STATUS_SUCCEEDED, result)
        _IDEMPOTENCY_REGISTRY[ikey] = result
        return result

    def get_audit_trail(self, job_id: str) -> List[Dict[str, Any]]:
        """Return all audit entries for *job_id* from the default in-memory log."""
        return [e for e in _DEFAULT_AUDIT_LOG if e.get("job_id") == job_id]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _execution_result(
        self,
        job_id: str,
        status: str,
        decision: Dict[str, Any],
        message: str = "",
        extras: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        base: Dict[str, Any] = {
            "job_id": job_id,
            "status": status,
            "project_id": decision.get("project_id"),
            "episode_id": decision.get("episode_id"),
            "changed_scene_id": decision.get("changed_scene_id"),
            "selected_strategy": decision.get("selected_strategy"),
            "rebuild_scene_ids": decision.get("rebuild_scene_ids", []),
            "decision": decision.get("decision"),
            "message": message,
            "executed_at": _now_iso(),
        }
        if extras:
            base.update(extras)
        return base

    def _record_audit(
        self,
        job_id: str,
        event: str,
        decision: Dict[str, Any],
        extras: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry: Dict[str, Any] = {
            "job_id": job_id,
            "event": event,
            "project_id": decision.get("project_id"),
            "episode_id": decision.get("episode_id"),
            "changed_scene_id": decision.get("changed_scene_id"),
            "selected_strategy": decision.get("selected_strategy"),
            "timestamp": _now_iso(),
        }
        if extras:
            entry.update(extras)
        try:
            self._audit_store(entry)
        except Exception as exc:  # noqa: BLE001
            _logger.warning("Audit store write failed for job %s: %s", job_id, exc)

    def _update_status(
        self,
        job_id: str,
        status: str,
        payload: Dict[str, Any],
    ) -> None:
        if self._status_updater:
            try:
                self._status_updater(job_id, status, payload)
            except Exception as exc:  # noqa: BLE001
                _logger.warning("Status updater failed for job %s: %s", job_id, exc)

    def _build_incident_payload(
        self,
        job_id: str,
        decision: Dict[str, Any],
        error: Exception,
    ) -> Dict[str, Any]:
        return {
            "job_id": job_id,
            "project_id": decision.get("project_id"),
            "episode_id": decision.get("episode_id"),
            "changed_scene_id": decision.get("changed_scene_id"),
            "selected_strategy": decision.get("selected_strategy"),
            "rebuild_scene_ids": decision.get("rebuild_scene_ids", []),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "severity": "high",
            "created_at": _now_iso(),
            "suggested_action": "Investigate rebuild logs and retry or escalate.",
        }

    @staticmethod
    def _noop_rebuild(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Default no-op rebuild function (replaced by real implementation)."""
        _logger.warning(
            "ApprovedRebuildExecutor: no rebuild_fn provided – noop called for job payload %s",
            payload,
        )
        return {"status": "noop", "payload": payload}


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()
