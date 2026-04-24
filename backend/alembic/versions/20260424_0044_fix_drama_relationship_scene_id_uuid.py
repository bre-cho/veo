"""fix drama_relationship_edges.last_interaction_scene_id to UUID

Revision ID: 20260424_0044
Revises: 20260424_0043
Create Date: 2026-04-24 22:49:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260424_0044"
down_revision = "20260424_0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Preflight: remove any rows whose last_interaction_scene_id is not a valid UUID.
    # This prevents the ::uuid cast from failing on dirty data.
    op.execute(
        """
        UPDATE drama_relationship_edges
        SET last_interaction_scene_id = NULL
        WHERE last_interaction_scene_id IS NOT NULL
          AND last_interaction_scene_id !~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        """
    )

    op.alter_column(
        "drama_relationship_edges",
        "last_interaction_scene_id",
        type_=postgresql.UUID(as_uuid=True),
        postgresql_using="last_interaction_scene_id::uuid",
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "drama_relationship_edges",
        "last_interaction_scene_id",
        type_=sa.String(length=128),
        postgresql_using="last_interaction_scene_id::text",
        nullable=True,
    )
