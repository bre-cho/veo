from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.render_incident_state import RenderIncidentState

SEGMENTS = ["active", "untriaged", "assigned", "muted", "resolved", "mine"]

_STALE_SECONDS = 1800
_HIGH_SEVERITY_RANK = 20


def _build_segment_flag(segment: str, ris: type, assignee: str | None = None):
    """Return a SQLAlchemy boolean expression that is truthy for rows in *segment*."""
    if segment == "untriaged":
        return (
            ris.acknowledged.is_(False)
            & ris.assigned_to.is_(None)
            & ris.resolved_at.is_(None)
        )
    if segment == "mine":
        if assignee:
            return ris.assigned_to == assignee
        # No assignee → no rows belong to "mine"
        return False
    if segment == "assigned":
        return ris.assigned_to.is_not(None) & ris.resolved_at.is_(None)
    if segment == "muted":
        return ris.muted.is_(True)
    if segment == "resolved":
        return ris.resolved_at.is_not(None)
    # "active" — everything not yet resolved
    return ris.resolved_at.is_(None)


def get_incident_segment_metrics(
    db: Session,
    *,
    provider: str | None = None,
    show_muted: bool = False,
    assignee: str | None = None,
) -> dict:
    """Return per-segment counts using a single SQL query instead of 6 full-table scans."""
    ris = RenderIncidentState
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Build the base filter (applied once, not per segment).
    base_filters = []
    if provider:
        base_filters.append(ris.provider == provider)
    if not show_muted:
        base_filters.append(ris.suppressed.is_(False))

    # We aggregate each segment as a separate COUNT(CASE WHEN … THEN 1 END) column.
    # This produces exactly one DB round-trip regardless of the number of segments.
    def _cnt(expr):
        """COUNT rows where *expr* is true."""
        return func.sum(case((expr, 1), else_=0))

    def _cnt_and(seg_expr, extra_expr):
        """COUNT rows that are in the segment AND satisfy *extra_expr*."""
        return func.sum(case(((seg_expr & extra_expr), 1), else_=0))

    segment_exprs = {seg: _build_segment_flag(seg, ris, assignee) for seg in SEGMENTS}

    # Sub-expressions reused across segments
    stale_threshold = now - timedelta(seconds=_STALE_SECONDS)
    unacked_expr = ris.acknowledged.is_(False)
    assigned_expr = ris.assigned_to.isnot(None)
    muted_expr = ris.muted.is_(True)
    resolved_expr = ris.resolved_at.isnot(None)
    stale_expr = ris.last_seen_at <= stale_threshold
    high_sev_expr = func.coalesce(ris.current_severity_rank, 0) >= _HIGH_SEVERITY_RANK

    # Build one aggregation query with all per-segment columns.
    # Each segment contributes 8 aggregate columns (total + 7 sub-counts).
    agg_cols = []
    seg_order = list(SEGMENTS)
    for seg in seg_order:
        se = segment_exprs[seg]
        if se is False:
            # "mine" with no assignee: all counts are 0, skip expensive columns
            agg_cols += [
                func.literal(0),  # total
                func.literal(0),  # unacknowledged
                func.literal(0),  # assigned
                func.literal(0),  # muted
                func.literal(0),  # resolved
                func.literal(0),  # stale_over_30m
                func.literal(0),  # high_severity
            ]
        else:
            agg_cols += [
                _cnt(se),
                _cnt_and(se, unacked_expr),
                _cnt_and(se, assigned_expr),
                _cnt_and(se, muted_expr),
                _cnt_and(se, resolved_expr),
                _cnt_and(se, stale_expr),
                _cnt_and(se, high_sev_expr),
            ]

    row = db.query(*agg_cols).filter(*base_filters).one()

    # Unpack the flat tuple into per-segment dicts.
    items = []
    for i, seg in enumerate(seg_order):
        base = i * 7
        items.append({
            "segment": seg,
            "total": int(row[base] or 0),
            "unacknowledged": int(row[base + 1] or 0),
            "assigned": int(row[base + 2] or 0),
            "muted": int(row[base + 3] or 0),
            "resolved": int(row[base + 4] or 0),
            "stale_over_30m": int(row[base + 5] or 0),
            "high_severity": int(row[base + 6] or 0),
        })

    return {"generated_at": now, "provider": provider, "show_muted": show_muted, "items": items}


def preview_bulk_action(db: Session, *, action_type: str, incident_keys: list[str], assigned_to: str | None = None, muted_until: datetime | None = None) -> dict:
    rows = db.query(RenderIncidentState).filter(RenderIncidentState.incident_key.in_(incident_keys)).all()
    by_key = {r.incident_key: r for r in rows}
    items = []
    eligible = 0
    for incident_key in incident_keys:
        row = by_key.get(incident_key)
        if not row:
            items.append({"incident_key": incident_key, "eligible": False, "reason": "incident_not_found"})
            continue
        reason = None
        is_eligible = True
        predicted_status = row.status
        predicted_assigned_to = row.assigned_to
        predicted_muted_until = row.muted_until
        if action_type == "acknowledge":
            if row.acknowledged:
                is_eligible = False
                reason = "already_acknowledged"
            else:
                predicted_status = "acknowledged"
        elif action_type == "assign":
            if not assigned_to:
                is_eligible = False
                reason = "missing_assigned_to"
            elif row.assigned_to == assigned_to and row.status == "assigned":
                is_eligible = False
                reason = "already_assigned_to_target"
            else:
                predicted_status = "assigned"
                predicted_assigned_to = assigned_to
        elif action_type == "mute":
            if row.muted and row.muted_until and muted_until and row.muted_until >= muted_until:
                is_eligible = False
                reason = "already_muted_longer"
            else:
                predicted_status = "muted"
                predicted_muted_until = muted_until
        elif action_type == "resolve":
            if row.resolved_at is not None or row.status == "resolved":
                is_eligible = False
                reason = "already_resolved"
            else:
                predicted_status = "resolved"
        if is_eligible:
            eligible += 1
        items.append({
            "incident_key": incident_key,
            "current_status": row.status,
            "assigned_to": row.assigned_to,
            "muted": row.muted,
            "acknowledged": row.acknowledged,
            "eligible": is_eligible,
            "reason": reason,
            "predicted_status": predicted_status,
            "predicted_assigned_to": predicted_assigned_to,
            "predicted_muted_until": predicted_muted_until,
        })
    return {"ok": True, "action_type": action_type, "attempted": len(incident_keys), "eligible": eligible, "skipped": len(incident_keys)-eligible, "items": items}
