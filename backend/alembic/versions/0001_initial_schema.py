from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "candidates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("willing_to_relocate", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("years_of_experience", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("seniority_level", sa.String(50), nullable=False, server_default="mid"),
        sa.Column('skills', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint("uq_candidates_email", "candidates", ["email"])

    op.create_table(
        "match_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_input", sa.Text(), nullable=False),
        sa.Column("job_description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("job_title", sa.String(255), nullable=True),
        sa.Column("required_seniority", sa.String(50), nullable=True),
        sa.Column("required_skills", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("overall_score", sa.SmallInteger(), nullable=True),
        sa.Column("skills_score", sa.SmallInteger(), nullable=True),
        sa.Column("experience_score", sa.SmallInteger(), nullable=True),
        sa.Column("location_score", sa.SmallInteger(), nullable=True),
        sa.Column("matched_skills", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("missing_skills", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("score_explanation", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("enqueued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("overall_score BETWEEN 0 AND 100", name="ck_match_jobs_overall_score"),
        sa.CheckConstraint("skills_score BETWEEN 0 AND 100", name="ck_match_jobs_skills_score"),
        sa.CheckConstraint("experience_score BETWEEN 0 AND 100", name="ck_match_jobs_experience_score"),
        sa.CheckConstraint("location_score BETWEEN 0 AND 100", name="ck_match_jobs_location_score"),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_match_jobs_status",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["candidates.id"],
            name="fk_match_jobs_candidate_id",
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "idx_match_jobs_candidate_status",
        "match_jobs",
        ["candidate_id", "status", "enqueued_at"],
    )
    op.create_index("idx_match_jobs_batch_id", "match_jobs", ["batch_id"])


def downgrade() -> None:
    op.drop_index("idx_match_jobs_batch_id")
    op.drop_index("idx_match_jobs_candidate_status")
    op.drop_table("match_jobs")
    op.drop_table("candidates")
