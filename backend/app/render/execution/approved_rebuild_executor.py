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
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Idempotency backend protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class IdempotencyBackend(Protocol):
    """Interface for pluggable idempotency storage.

    Production implementations persist to a database or Redis.  The
    ``_InMemoryIdempotency`` class below is used as the default for
    single-process testing only.

    The atomic reserve/complete pattern eliminates the check-then-act race
    condition present in plain check() / store() flows:

    * ``reserve_key`` atomically claims a key (e.g. via INSERT with unique
      constraint).  Returns ``True`` on success, ``False`` if the key was
      already claimed by another request.
    * ``complete_key`` updates the reserved entry to its final state once
      the rebuild has finished (succeeded or failed).
    * ``check`` / ``store`` are retained for backward compatibility.
    """

    def check(self, key: str) -> Optional[Dict[str, Any]]:
        """Return a previously stored result dict, or ``None``."""
        ...

    def store(self, key: str, result: Dict[str, Any]) -> None:
        """Persist a result dict under *key*."""
        ...

    def reserve_key(self, key: str, job_id: str) -> bool:
        """Atomically claim *key* with status executing.

        Returns ``True`` if the key was successfully reserved (no prior entry),
        ``False`` if the key already exists (duplicate / concurrent request).
        """
        ...

    def complete_key(self, key: str, result: Dict[str, Any]) -> None:
        """Update the reserved entry to its final result."""
        ...


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
# In-memory idempotency backend (single-process / testing use only)
# ---------------------------------------------------------------------------


class _InMemoryIdempotency:
    """In-memory idempotency backend.

    Suitable for single-process development and unit tests only.
    Uses a threading lock so that ``reserve_key`` is thread-safe.
    Use :class:`~app.render.execution.rebuild_persistence.DbRebuildPersistence`
    in production.
    """

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def reserve_key(self, key: str, job_id: str) -> bool:
        """Atomically claim *key*.  Returns True if reserved, False if duplicate."""
        with self._lock:
            if key in self._store:
                return False
            self._store[key] = {"job_id": job_id, "status": STATUS_EXECUTING}
            return True

    def complete_key(self, key: str, result: Dict[str, Any]) -> None:
        """Update a previously reserved key to its final result."""
        with self._lock:
            self._store[key] = result

    def check(self, key: str) -> Optional[Dict[str, Any]]:
        return self._store.get(key)

    def store(self, key: str, result: Dict[str, Any]) -> None:
        self._store[key] = result


# Module-level singleton kept for backward-compat with tests that call
# get_default_audit_log / clear_default_audit_log.
_DEFAULT_IDEMPOTENCY = _InMemoryIdempotency()


# ---------------------------------------------------------------------------
# Preflight validator
# ---------------------------------------------------------------------------

#: Decisions older than this many seconds are considered expired and will be
#: rejected by ``RebuildPreflightValidator``.  The ``decided_at`` field must be
#: present in the decision payload for the TTL check to apply.
DECISION_MAX_AGE_SECONDS: int = 300  # 5 minutes


class RebuildPreflightValidator:
    """Lightweight sanity checks performed *before* executing a rebuild.

    All checks operate on the decision payload dict — no database or filesystem
    access is required.  Expensive infra-backed checks (e.g. "does the project
    still exist in the DB?") belong in a separate, heavier validation layer.

    Checks performed
    ----------------
    1. Required fields present: project_id, episode_id, changed_scene_id.
    2. rebuild_scene_ids is a non-empty list.
    3. Decision action is not already ``block``.
    4. Decision has not expired (if ``decided_at`` ISO timestamp is present and
       the age exceeds :data:`DECISION_MAX_AGE_SECONDS`).
    """

    @staticmethod
    def validate(decision: Dict[str, Any]) -> Dict[str, Any]:
        """Validate *decision* and return a result dict.

        Returns:
            ``{"valid": True, "reason": ""}`` on success, or
            ``{"valid": False, "reason": "<explanation>"}`` on failure.
        """
        # ── 1. Required fields ──────────────────────────────────────────
        for field in ("project_id", "episode_id", "changed_scene_id"):
            if not decision.get(field):
                return {"valid": False, "reason": f"Missing required field: {field}"}

        # ── 2. Non-empty scene list ─────────────────────────────────────
        rebuild_scene_ids = decision.get("rebuild_scene_ids") or []
        if not rebuild_scene_ids:
            return {"valid": False, "reason": "rebuild_scene_ids is empty"}
        if not isinstance(rebuild_scene_ids, (list, tuple)):
            return {"valid": False, "reason": "rebuild_scene_ids must be a list"}

        # ── 3. Decision not already blocked ────────────────────────────
        # Accept both "block" (raw engine value) and "blocked" (executor status).
        raw_decision = decision.get("decision", "")
        if raw_decision in (STATUS_BLOCKED, "block"):
            return {
                "valid": False,
                "reason": "Decision is blocked by budget guard — cannot execute",
            }

        # ── 4. Decision TTL ─────────────────────────────────────────────
        decided_at = decision.get("decided_at")
        if decided_at:
            try:
                dt = datetime.fromisoformat(decided_at)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                age_sec = (datetime.now(tz=timezone.utc) - dt).total_seconds()
                if age_sec > DECISION_MAX_AGE_SECONDS:
                    return {
                        "valid": False,
                        "reason": (
                            f"Decision has expired "
                            f"(age={age_sec:.0f}s > {DECISION_MAX_AGE_SECONDS}s). "
                            "Re-run /decide to obtain a fresh decision."
                        ),
                    }
            except (ValueError, TypeError):
                pass  # Malformed decided_at — skip TTL check rather than block

        return {"valid": True, "reason": ""}


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
        idempotency_backend: Optional[IdempotencyBackend] = None,
    ) -> None:
        self._rebuild_fn = rebuild_fn or self._noop_rebuild
        self._status_updater = status_updater
        self._audit_store = audit_store or _default_append_audit
        self._idempotency: IdempotencyBackend = idempotency_backend or _DEFAULT_IDEMPOTENCY

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
        1. Guard: reject blocked / downgraded decisions without a scene list.
        2. Atomic reserve: call ``reserve_key()`` — if it returns False another
           request already claimed this key; return the cached result.
        3. Preflight validation via :class:`RebuildPreflightValidator`.
        4. Transition: queued → approved → executing.
        5. Call rebuild function.
        6. Transition: executing → succeeded | failed → incident_required.
        7. Persist final result via ``complete_key()``.
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

        # Normalize engine action names ("block"/"downgrade") to the executor's
        # canonical status values ("blocked"/"downgraded").  The engine produces
        # short forms; the executor uses longer forms internally.
        action = decision.get("decision", "block")
        if action == "block":
            action = STATUS_BLOCKED
        elif action == "downgrade":
            action = STATUS_DOWNGRADED

        # ── Guard: blocked or downgraded decisions are not executable ──
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

        # ── Atomic reserve — eliminates check-then-act race condition ──
        reserved = self._idempotency.reserve_key(ikey, job_id)
        if not reserved:
            # Another request already claimed this key.
            existing = self._idempotency.check(ikey)
            if existing is not None:
                _logger.info(
                    "Idempotency hit for job %s (key=%s): returning cached result %s",
                    job_id,
                    ikey,
                    existing.get("status"),
                )
                return existing
            # Edge case: key was reserved but result not yet written (concurrent)
            return self._execution_result(
                job_id=job_id,
                status=STATUS_EXECUTING,
                decision=decision,
                message="Rebuild already in progress for this idempotency key.",
            )

        # ── Transition: queued → approved ──────────────────────────────
        self._record_audit(job_id=job_id, event=STATUS_APPROVED, decision=decision)
        self._update_status(
            job_id,
            STATUS_APPROVED,
            {"message": "Rebuild approved, execution starting."},
        )

        # ── Preflight validation ────────────────────────────────────────
        preflight = RebuildPreflightValidator.validate(decision)
        if not preflight["valid"]:
            result = self._execution_result(
                job_id=job_id,
                status=STATUS_BLOCKED,
                decision=decision,
                message=f"Preflight check failed: {preflight['reason']}",
            )
            self._record_audit(
                job_id=job_id,
                event="preflight_failed",
                decision=decision,
                extras={"reason": preflight["reason"]},
            )
            self._update_status(job_id, STATUS_BLOCKED, result)
            self._idempotency.complete_key(ikey, result)
            return result

        # ── Revalidate scene list ───────────────────────────────────────
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
            self._idempotency.complete_key(ikey, result)
            return result

        # ── Transition: approved → executing ───────────────────────────
        self._record_audit(job_id=job_id, event=STATUS_EXECUTING, decision=decision)
        self._update_status(
            job_id,
            STATUS_EXECUTING,
            {"rebuild_scene_ids": rebuild_scene_ids},
        )

        # ── Execute rebuild ─────────────────────────────────────────────
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
            self._idempotency.complete_key(ikey, result)
            return result

        # ── Transition: executing → succeeded ──────────────────────────
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
        self._idempotency.complete_key(ikey, result)
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
