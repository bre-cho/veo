from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.db.session import SessionLocal
from app.models.production_run import ProductionRun
from app.models.production_timeline_event import ProductionTimelineEvent


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _run_to_dict(row: ProductionRun) -> dict[str, Any]:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "render_job_id": row.render_job_id,
        "trace_id": row.trace_id,
        "title": row.title,
        "current_stage": row.current_stage,
        "status": row.status,
        "percent_complete": row.percent_complete,
        "blocking_reason": row.blocking_reason,
        "active_worker": row.active_worker,
        "output_readiness": row.output_readiness,
        "output_url": row.output_url,
        "last_event_at": row.last_event_at,
        "started_at": row.started_at,
        "completed_at": row.completed_at,
        "metadata_json": {},
    }


def _event_to_dict(row: ProductionTimelineEvent) -> dict[str, Any]:
    details = None
    if row.details_json:
        try:
            details = json.loads(row.details_json)
        except json.JSONDecodeError:
            details = {"raw": row.details_json}
    return {
        "id": row.id,
        "production_run_id": row.production_run_id,
        "project_id": row.project_id,
        "render_job_id": row.render_job_id,
        "trace_id": row.trace_id,
        "title": row.title,
        "message": row.message,
        "phase": row.phase,
        "stage": row.stage,
        "event_type": row.event_type,
        "status": row.status,
        "worker_name": row.worker_name,
        "provider": row.provider,
        "progress_percent": row.progress_percent,
        "is_blocking": row.is_blocking,
        "is_operator_action": row.is_operator_action,
        "occurred_at": row.occurred_at,
        "details": details,
        "details_json": row.details_json,
    }


class TimelineRepository:
    def __init__(self) -> None:
        self._memory_runs: dict[str, dict[str, Any]] = {}
        self._memory_events: dict[str, list[dict[str, Any]]] = {}
        self._allow_fallback = os.getenv("TIMELINE_DB_FALLBACK_ENABLED", "1") == "1"

    @property
    def runs(self) -> dict[str, dict[str, Any]]:
        """Backward-compatible access to in-memory runs storage."""
        return self._memory_runs

    @property
    def events(self) -> dict[str, list[dict[str, Any]]]:
        """Backward-compatible access to in-memory events storage."""
        return self._memory_events

    def _with_memory_metadata(self, run: dict[str, Any]) -> dict[str, Any]:
        stored = self._memory_runs.get(run["id"], {})
        merged = dict(run)
        merged["metadata_json"] = dict(stored.get("metadata_json") or {})
        return merged

    def _memory_upsert_run(self, run: dict[str, Any]) -> dict[str, Any]:
        existing = self._memory_runs.get(run["id"], {})
        merged = {**existing, **run}
        metadata = run.get("metadata_json")
        if metadata is None:
            metadata = existing.get("metadata_json")
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        merged["metadata_json"] = metadata or {}
        self._memory_runs[run["id"]] = merged
        self._memory_events.setdefault(run["id"], [])
        return dict(merged)

    def _memory_get_run(self, run_id: str) -> dict[str, Any] | None:
        run = self._memory_runs.get(run_id)
        return dict(run) if run else None

    def _memory_list_runs(self) -> list[dict[str, Any]]:
        return [dict(run) for run in self._memory_runs.values()]

    def _memory_add_event(self, event: dict[str, Any]) -> dict[str, Any]:
        run_id = event["production_run_id"]
        entry = dict(event)
        self._memory_events.setdefault(run_id, []).append(entry)
        return dict(entry)

    def _memory_list_events_for_run(self, run_id: str) -> list[dict[str, Any]]:
        return [dict(event) for event in self._memory_events.get(run_id, [])]

    def upsert_run(self, run: dict[str, Any]) -> dict[str, Any]:
        self._memory_upsert_run(run)
        try:
            with SessionLocal() as db:
                row = db.query(ProductionRun).filter(ProductionRun.id == run["id"]).first()
                if row is None:
                    row = ProductionRun(id=run["id"])
                    db.add(row)

                row.project_id = run.get("project_id")
                row.render_job_id = run.get("render_job_id")
                row.trace_id = run.get("trace_id")
                row.title = run.get("title")
                row.current_stage = run.get("current_stage") or row.current_stage or "queued"
                row.status = run.get("status") or row.status or "queued"
                row.percent_complete = int(run.get("percent_complete") or 0)
                row.blocking_reason = run.get("blocking_reason")
                row.active_worker = run.get("active_worker")
                row.output_readiness = run.get("output_readiness") or row.output_readiness or "not_ready"
                row.output_url = run.get("output_url")
                row.last_event_at = _as_utc(run.get("last_event_at"))
                row.started_at = _as_utc(run.get("started_at"))
                row.completed_at = _as_utc(run.get("completed_at"))

                db.commit()
                db.refresh(row)
                return self._with_memory_metadata(_run_to_dict(row))
        except (OperationalError, SQLAlchemyError):
            if not self._allow_fallback:
                raise
            return self._memory_get_run(run["id"]) or self._memory_upsert_run(run)

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        try:
            with SessionLocal() as db:
                row = db.query(ProductionRun).filter(ProductionRun.id == run_id).first()
                if not row:
                    return self._memory_get_run(run_id)
                return self._with_memory_metadata(_run_to_dict(row))
        except (OperationalError, SQLAlchemyError):
            if not self._allow_fallback:
                raise
            return self._memory_get_run(run_id)

    def list_runs(self) -> list[dict[str, Any]]:
        try:
            with SessionLocal() as db:
                rows = db.query(ProductionRun).all()
                if not rows:
                    return self._memory_list_runs()
                return [self._with_memory_metadata(_run_to_dict(row)) for row in rows]
        except (OperationalError, SQLAlchemyError):
            if not self._allow_fallback:
                raise
            return self._memory_list_runs()

    def add_event(self, event: dict[str, Any]) -> dict[str, Any]:
        self._memory_add_event(event)
        try:
            with SessionLocal() as db:
                details_json = event.get("details_json")
                if details_json is None:
                    details_json = json.dumps(event.get("details") or {}, ensure_ascii=False)

                row = ProductionTimelineEvent(
                    id=event["id"],
                    production_run_id=event["production_run_id"],
                    project_id=event.get("project_id"),
                    render_job_id=event.get("render_job_id"),
                    trace_id=event.get("trace_id"),
                    phase=event["phase"],
                    stage=event["stage"],
                    event_type=event["event_type"],
                    status=event["status"],
                    worker_name=event.get("worker_name"),
                    provider=event.get("provider"),
                    title=event["title"],
                    message=event.get("message"),
                    details_json=details_json,
                    progress_percent=event.get("progress_percent"),
                    is_blocking=bool(event.get("is_blocking")),
                    is_operator_action=bool(event.get("is_operator_action")),
                    occurred_at=_as_utc(event.get("occurred_at")) or datetime.now(timezone.utc).replace(tzinfo=None),
                )
                db.add(row)
                db.commit()
                db.refresh(row)
                return _event_to_dict(row)
        except (OperationalError, SQLAlchemyError):
            if not self._allow_fallback:
                raise
            return dict(event)

    def list_events_for_run(self, run_id: str) -> list[dict[str, Any]]:
        try:
            with SessionLocal() as db:
                rows = (
                    db.query(ProductionTimelineEvent)
                    .filter(ProductionTimelineEvent.production_run_id == run_id)
                    .order_by(ProductionTimelineEvent.occurred_at.asc())
                    .all()
                )
                if not rows:
                    return self._memory_list_events_for_run(run_id)
                return [_event_to_dict(row) for row in rows]
        except (OperationalError, SQLAlchemyError):
            if not self._allow_fallback:
                raise
            return self._memory_list_events_for_run(run_id)


# Backward compatible alias used by existing imports.
InMemoryTimelineRepository = TimelineRepository
