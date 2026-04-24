"""add status and error_message to music_assets

Revision ID: 20260424_0042
Revises: 20260424_0041
Create Date: 2026-04-24 11:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260424_0042"
down_revision = "20260424_0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("music_assets", sa.Column("status", sa.String(length=32), nullable=False, server_default="succeeded"))
    op.add_column("music_assets", sa.Column("error_message", sa.Text(), nullable=True))
    op.create_index(op.f("ix_music_assets_status"), "music_assets", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_music_assets_status"), table_name="music_assets")
    op.drop_column("music_assets", "error_message")
    op.drop_column("music_assets", "status")
