"""Add durable jobs table

Revision ID: 202603030001
Revises: 202507200001
Create Date: 2026-03-03 00:01:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202603030001"
down_revision: str | Sequence[str] | None = "202507200001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_type", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'queued'"),
        ),
        sa.Column(
            "attempt",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "max_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("5"),
        ),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=255), nullable=True),
        sa.Column("correlation_id", sa.String(length=255), nullable=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("candidate_session_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["candidate_session_id"], ["candidate_sessions.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_jobs_status_next_run_created",
        "jobs",
        ["status", "next_run_at", "created_at"],
        unique=False,
    )
    op.create_index("ix_jobs_company_id", "jobs", ["company_id"], unique=False)
    op.create_index(
        "ix_jobs_candidate_session_id", "jobs", ["candidate_session_id"], unique=False
    )
    op.create_index(
        "uq_jobs_company_job_type_idempotency_key",
        "jobs",
        ["company_id", "job_type", "idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_jobs_company_job_type_idempotency_key", table_name="jobs")
    op.drop_index("ix_jobs_candidate_session_id", table_name="jobs")
    op.drop_index("ix_jobs_company_id", table_name="jobs")
    op.drop_index("ix_jobs_status_next_run_created", table_name="jobs")
    op.drop_table("jobs")
