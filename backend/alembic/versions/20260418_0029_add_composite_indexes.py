"""Add composite indexes for common query patterns

Revision ID: 20260418_0029
Revises: 20260417_0028
Create Date: 2026-04-18 00:00:00.000000

Rationale
---------
The following hot query patterns benefit from composite indexes:

1. Incident feed  (render_incident_states):
   - ORDER BY status ASC, current_severity_rank DESC, last_seen_at DESC
     filtered by suppressed=False  →  (status, suppressed, current_severity_rank, last_seen_at)
   - Filtered by provider + status + suppressed
     →  (provider, status, suppressed)

2. Jobs listing  (render_jobs):
   - Filtered by health_status, ORDER BY created_at DESC
     →  (health_status, created_at)
   - Filtered by provider + health_status, ORDER BY created_at DESC
     →  (provider, health_status, created_at)

3. Transition summary  (render_timeline_events):
   - Filtered by event_type IN (...) AND occurred_at >= since
     →  (event_type, occurred_at)
"""

from alembic import op

revision = "20260418_0029"
down_revision = "20260417_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- render_incident_states ---
    op.create_index(
        "ix_ris_status_suppressed_severity_lastseen",
        "render_incident_states",
        ["status", "suppressed", "current_severity_rank", "last_seen_at"],
    )
    op.create_index(
        "ix_ris_provider_status_suppressed",
        "render_incident_states",
        ["provider", "status", "suppressed"],
    )

    # --- render_jobs ---
    op.create_index(
        "ix_rj_health_status_created_at",
        "render_jobs",
        ["health_status", "created_at"],
    )
    op.create_index(
        "ix_rj_provider_health_created_at",
        "render_jobs",
        ["provider", "health_status", "created_at"],
    )

    # --- render_timeline_events ---
    op.create_index(
        "ix_rte_event_type_occurred_at",
        "render_timeline_events",
        ["event_type", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_rte_event_type_occurred_at", table_name="render_timeline_events")
    op.drop_index("ix_rj_provider_health_created_at", table_name="render_jobs")
    op.drop_index("ix_rj_health_status_created_at", table_name="render_jobs")
    op.drop_index("ix_ris_provider_status_suppressed", table_name="render_incident_states")
    op.drop_index("ix_ris_status_suppressed_severity_lastseen", table_name="render_incident_states")
