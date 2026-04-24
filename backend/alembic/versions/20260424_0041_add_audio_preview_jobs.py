"""add audio_preview_jobs table

Revision ID: 20260424_0041
Revises: 20260424_0040
Create Date: 2026-04-24 08:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260424_0041"
down_revision = "20260424_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audio_preview_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("voice_profile_id", sa.String(length=36), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("style_preset", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("preview_url", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audio_preview_jobs")),
    )
    op.create_index(op.f("ix_audio_preview_jobs_voice_profile_id"), "audio_preview_jobs", ["voice_profile_id"], unique=False)
    op.create_index(op.f("ix_audio_preview_jobs_status"), "audio_preview_jobs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audio_preview_jobs_status"), table_name="audio_preview_jobs")
    op.drop_index(op.f("ix_audio_preview_jobs_voice_profile_id"), table_name="audio_preview_jobs")
    op.drop_table("audio_preview_jobs")
