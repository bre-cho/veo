"""init poster engine schema

Revision ID: 20260505_0001
Revises:
Create Date: 2026-05-05 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260505_0001"
down_revision = None
branch_labels = None
depends_on = None


project_status_enum = sa.Enum(
    "draft", "generating", "scored", "exported", "failed", name="projectstatus"
)
job_status_enum = sa.Enum("queued", "running", "done", "failed", name="jobstatus")


def upgrade() -> None:
    bind = op.get_bind()
    project_status_enum.create(bind, checkfirst=True)
    job_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "brands",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("industry", sa.String(), nullable=True),
        sa.Column("colors", sa.JSON(), nullable=True),
        sa.Column("fonts", sa.JSON(), nullable=True),
        sa.Column("brand_voice", sa.Text(), nullable=True),
        sa.Column("logo_asset_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "assets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(), nullable=True),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("brand_id", sa.String(), nullable=False),
        sa.Column("campaign_type", sa.String(), nullable=True),
        sa.Column("product_name", sa.String(), nullable=False),
        sa.Column("target_customer", sa.String(), nullable=True),
        sa.Column("offer", sa.String(), nullable=True),
        sa.Column("status", project_status_enum, nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("job_type", sa.String(), nullable=False),
        sa.Column("status", job_status_enum, nullable=True),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("input_json", sa.JSON(), nullable=True),
        sa.Column("output_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "poster_variants",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("variant_type", sa.String(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("image_asset_id", sa.String(), nullable=True),
        sa.Column("canva_design_id", sa.String(), nullable=True),
        sa.Column("adobe_asset_id", sa.String(), nullable=True),
        sa.Column("ctr_score", sa.Float(), nullable=True),
        sa.Column("attention_score", sa.Float(), nullable=True),
        sa.Column("luxury_score", sa.Float(), nullable=True),
        sa.Column("trust_score", sa.Float(), nullable=True),
        sa.Column("product_focus", sa.Float(), nullable=True),
        sa.Column("conversion_score", sa.Float(), nullable=True),
        sa.Column("final_score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_projects_brand_id", "projects", ["brand_id"])
    op.create_index("ix_projects_created_at", "projects", ["created_at"])
    op.create_index("ix_poster_variants_project_id", "poster_variants", ["project_id"])
    op.create_index("ix_poster_variants_created_at", "poster_variants", ["created_at"])
    op.create_index("ix_jobs_created_at", "jobs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_jobs_created_at", table_name="jobs")
    op.drop_index("ix_poster_variants_created_at", table_name="poster_variants")
    op.drop_index("ix_poster_variants_project_id", table_name="poster_variants")
    op.drop_index("ix_projects_created_at", table_name="projects")
    op.drop_index("ix_projects_brand_id", table_name="projects")

    op.drop_table("poster_variants")
    op.drop_table("jobs")
    op.drop_table("projects")
    op.drop_table("assets")
    op.drop_table("brands")

    bind = op.get_bind()
    job_status_enum.drop(bind, checkfirst=True)
    project_status_enum.drop(bind, checkfirst=True)
