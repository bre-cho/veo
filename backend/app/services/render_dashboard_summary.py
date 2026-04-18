from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.render_incident_state import RenderIncidentState
from app.models.render_job import RenderJob
from app.models.render_timeline_event import RenderTimelineEvent

HEALTH_EVENTS = {
    'job_health_degraded', 'job_health_stalled', 'job_health_recovered', 'job_health_failed', 'job_health_completed', 'job_health_healthy', 'job_health_queued'
}

# Health status keys tracked in provider breakdown
_PROVIDER_HS_KEYS = ('healthy', 'degraded', 'stalled', 'failed', 'completed', 'queued')
# Event-type suffixes tracked in transition summaries
_TRANSITION_KEYS = ('degraded', 'stalled', 'recovered', 'failed', 'completed')


def _transition_summary(db: Session, window: timedelta, label: str) -> dict:
    """Return health-event transition counts for *window* using a single aggregating query."""
    since = datetime.now(timezone.utc).replace(tzinfo=None) - window
    rows = (
        db.query(RenderTimelineEvent.event_type, func.count().label('cnt'))
        .filter(
            RenderTimelineEvent.event_type.in_(list(HEALTH_EVENTS)),
            RenderTimelineEvent.occurred_at >= since,
        )
        .group_by(RenderTimelineEvent.event_type)
        .all()
    )
    type_counts: dict[str, int] = {event_type: cnt for event_type, cnt in rows}
    total = sum(type_counts.values())
    return {
        'window': label,
        'total_transitions': total,
        **{f'{k}_transitions': type_counts.get(f'job_health_{k}', 0) for k in _TRANSITION_KEYS},
    }


def get_render_dashboard_summary(db: Session) -> dict:
    """Return dashboard summary stats using SQL aggregation instead of Python loops."""
    # --- Health-status counts + scene-count aggregates ---
    health_rows = (
        db.query(
            func.coalesce(RenderJob.health_status, 'queued').label('hs'),
            func.count(RenderJob.id).label('cnt'),
            func.coalesce(func.sum(RenderJob.active_scene_count), 0).label('active'),
            func.coalesce(func.sum(RenderJob.stalled_scene_count), 0).label('stalled'),
            func.coalesce(func.sum(RenderJob.degraded_scene_count), 0).label('degraded'),
        )
        .group_by(func.coalesce(RenderJob.health_status, 'queued'))
        .all()
    )

    counts: dict[str, int] = {k: 0 for k in _PROVIDER_HS_KEYS}
    total_jobs = total_active = total_stalled = total_degraded = 0
    for hs, cnt, active, stalled, degraded in health_rows:
        counts[hs] = counts.get(hs, 0) + cnt
        total_jobs += cnt
        total_active += int(active)
        total_stalled += int(stalled)
        total_degraded += int(degraded)

    # --- Provider breakdown ---
    provider_rows = (
        db.query(
            RenderJob.provider,
            func.coalesce(RenderJob.health_status, 'queued').label('hs'),
            func.count(RenderJob.id).label('cnt'),
        )
        .group_by(RenderJob.provider, func.coalesce(RenderJob.health_status, 'queued'))
        .all()
    )
    by_provider: dict[str, dict] = {}
    for provider, hs, cnt in provider_rows:
        item = by_provider.setdefault(provider, {
            'provider': provider, 'total_jobs': 0,
            **{f'{k}_jobs': 0 for k in _PROVIDER_HS_KEYS},
        })
        item['total_jobs'] += cnt
        key = f'{hs}_jobs'
        if key in item:
            item[key] += cnt

    return {
        'total_jobs': total_jobs,
        'healthy_jobs': counts.get('healthy', 0),
        'degraded_jobs': counts.get('degraded', 0),
        'stalled_jobs': counts.get('stalled', 0),
        'failed_jobs': counts.get('failed', 0),
        'completed_jobs': counts.get('completed', 0),
        'queued_jobs': counts.get('queued', 0),
        'total_active_scenes': total_active,
        'total_stalled_scenes': total_stalled,
        'total_degraded_scenes': total_degraded,
        'counts_by_provider': list(by_provider.values()),
        'recent_transitions': [
            _transition_summary(db, timedelta(hours=1), '1h'),
            _transition_summary(db, timedelta(hours=24), '24h'),
        ],
    }


def get_recent_incidents(
    db: Session,
    *,
    limit: int = 20,
    provider: str | None = None,
    show_muted: bool = False,
    workflow_status: str | None = None,
    assigned_to: str | None = None,
    segment: str | None = None,
) -> dict:
    """Fetch recent incidents with a single JOIN query to avoid N+1 per-incident job lookups."""
    q = (
        db.query(RenderIncidentState, RenderJob)
        .outerjoin(RenderJob, RenderJob.id == RenderIncidentState.job_id)
        .order_by(
            RenderIncidentState.status.asc(),
            RenderIncidentState.current_severity_rank.desc(),
            RenderIncidentState.last_seen_at.desc(),
        )
    )
    if provider:
        q = q.filter(RenderIncidentState.provider == provider)
    if workflow_status:
        q = q.filter(RenderIncidentState.status == workflow_status)
    if assigned_to:
        q = q.filter(RenderIncidentState.assigned_to == assigned_to)
    if segment == "untriaged":
        q = q.filter(
            RenderIncidentState.acknowledged.is_(False),
            RenderIncidentState.assigned_to.is_(None),
            RenderIncidentState.resolved_at.is_(None),
        )
    elif segment == "mine":
        if assigned_to:
            q = q.filter(RenderIncidentState.assigned_to == assigned_to)
    elif segment == "assigned":
        q = q.filter(
            RenderIncidentState.assigned_to.is_not(None),
            RenderIncidentState.resolved_at.is_(None),
        )
    elif segment == "muted":
        q = q.filter(RenderIncidentState.muted.is_(True))
    elif segment == "resolved":
        q = q.filter(RenderIncidentState.resolved_at.is_not(None))
    elif segment == "active":
        q = q.filter(RenderIncidentState.resolved_at.is_(None))
    if not show_muted:
        q = q.filter(RenderIncidentState.suppressed.is_(False))

    results = q.limit(limit).all()
    items = []
    for state, job in results:
        items.append({
            'event_id': state.current_event_id or state.id,
            'incident_key': state.incident_key,
            'event_type': state.current_event_type or 'incident_open',
            'occurred_at': state.last_seen_at,
            'previous_status': None,
            'current_status': state.status,
            'previous_reason': None,
            'current_reason': state.suppression_reason or state.note,
            'workflow_status': state.status,
            'acknowledged': state.acknowledged,
            'muted': state.muted,
            'assigned_to': state.assigned_to,
            'job': {
                'job_id': state.job_id,
                'project_id': state.project_id,
                'provider': state.provider,
                'status': job.status if job else 'unknown',
                'health_status': job.health_status if job else None,
                'health_reason': job.health_reason if job else None,
                'planned_scene_count': job.planned_scene_count if job else 0,
                'processing_scene_count': job.processing_scene_count if job else 0,
                'succeeded_scene_count': job.completed_scene_count if job else 0,
                'failed_scene_count_snapshot': job.failed_scene_count_snapshot if job else 0,
                'stalled_scene_count': job.stalled_scene_count if job else 0,
                'degraded_scene_count': job.degraded_scene_count if job else 0,
                'active_scene_count': job.active_scene_count if job else 0,
                'created_at': job.created_at if job else None,
                'updated_at': job.updated_at if job else None,
                'last_event_at': job.last_event_at if job else None,
                'last_health_transition_at': job.last_health_transition_at if job else None,
            },
            'payload': {},
        })
    return {'items': items, 'limit': limit, 'total_returned': len(items), 'next_cursor': None}
