"""add rag_documents and ml_recommendation_log tables

Revision ID: 20260417_0028
Revises: 20260415_0027
Create Date: 2026-04-17 11:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20260417_0028"
down_revision = "20260415_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rag_documents",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("chunk_id", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=512), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("char_end", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_rag_documents_chunk_id", "rag_documents", ["chunk_id"])
    op.create_index("ix_rag_documents_source", "rag_documents", ["source"])

    op.create_table(
        "ml_recommendation_log",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("job_id", sa.String(length=36), nullable=True),
        sa.Column("predictor_version", sa.String(length=64), nullable=False,
                  server_default="v1"),
        sa.Column("fail_risk", sa.Float(), nullable=True),
        sa.Column("slow_render", sa.Float(), nullable=True),
        sa.Column("feature_snapshot", sa.JSON(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ml_recommendation_log_job_id", "ml_recommendation_log", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_ml_recommendation_log_job_id", table_name="ml_recommendation_log")
    op.drop_table("ml_recommendation_log")
    op.drop_index("ix_rag_documents_source", table_name="rag_documents")
    op.drop_index("ix_rag_documents_chunk_id", table_name="rag_documents")
    op.drop_table("rag_documents")
