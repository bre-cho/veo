"""add error_artifact_url to audio_render_outputs

Revision ID: 20260424_0043
Revises: 20260424_0042
Create Date: 2026-04-24 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260424_0043"
down_revision = "20260424_0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audio_render_outputs",
        sa.Column("error_artifact_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("audio_render_outputs", "error_artifact_url")
