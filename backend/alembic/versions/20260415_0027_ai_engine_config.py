"""add ai_engine_config table for OpenRouter key storage

Revision ID: 20260415_0027
Revises: 20260415_0026
Create Date: 2026-04-15 03:52:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20260415_0027"
down_revision = "20260415_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_engine_config",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("openrouter_api_key", sa.Text(), nullable=True),
        sa.Column("default_model", sa.String(length=128), nullable=True, server_default="openai/gpt-4o-mini"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True,
                  server_default=sa.text("NOW()")),
    )


def downgrade() -> None:
    op.drop_table("ai_engine_config")
