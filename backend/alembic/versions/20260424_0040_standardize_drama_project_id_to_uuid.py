"""standardize drama project_id to uuid

Revision ID: 20260424_0040
Revises: 20260424_0039
Create Date: 2026-04-24 05:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260424_0040"
down_revision = "20260424_0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # drama_character_profiles: project_id VARCHAR(128) -> UUID
    op.drop_index("ix_drama_character_profiles_project_id", table_name="drama_character_profiles")
    op.alter_column(
        "drama_character_profiles",
        "project_id",
        type_=postgresql.UUID(as_uuid=True),
        postgresql_using="project_id::uuid",
        nullable=False,
    )
    op.create_index(
        "ix_drama_character_profiles_project_id",
        "drama_character_profiles",
        ["project_id"],
        unique=False,
    )

    # drama_relationship_edges: project_id VARCHAR(128) -> UUID
    # Also need to drop the unique constraint that references project_id before altering
    op.drop_index("ix_drama_relationship_edges_project_id", table_name="drama_relationship_edges")
    op.drop_constraint(
        "uq_drama_relationship_edges_project_pair",
        table_name="drama_relationship_edges",
        type_="unique",
    )
    op.alter_column(
        "drama_relationship_edges",
        "project_id",
        type_=postgresql.UUID(as_uuid=True),
        postgresql_using="project_id::uuid",
        nullable=False,
    )
    op.create_index(
        "ix_drama_relationship_edges_project_id",
        "drama_relationship_edges",
        ["project_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_drama_relationship_edges_project_pair",
        "drama_relationship_edges",
        ["project_id", "source_character_id", "target_character_id"],
    )


def downgrade() -> None:
    # drama_relationship_edges: UUID -> VARCHAR(128)
    op.drop_index("ix_drama_relationship_edges_project_id", table_name="drama_relationship_edges")
    op.drop_constraint(
        "uq_drama_relationship_edges_project_pair",
        table_name="drama_relationship_edges",
        type_="unique",
    )
    op.alter_column(
        "drama_relationship_edges",
        "project_id",
        type_=sa.String(length=128),
        postgresql_using="project_id::text",
        nullable=False,
    )
    op.create_index(
        "ix_drama_relationship_edges_project_id",
        "drama_relationship_edges",
        ["project_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_drama_relationship_edges_project_pair",
        "drama_relationship_edges",
        ["project_id", "source_character_id", "target_character_id"],
    )

    # drama_character_profiles: UUID -> VARCHAR(128)
    op.drop_index("ix_drama_character_profiles_project_id", table_name="drama_character_profiles")
    op.alter_column(
        "drama_character_profiles",
        "project_id",
        type_=sa.String(length=128),
        postgresql_using="project_id::text",
        nullable=False,
    )
    op.create_index(
        "ix_drama_character_profiles_project_id",
        "drama_character_profiles",
        ["project_id"],
        unique=False,
    )
