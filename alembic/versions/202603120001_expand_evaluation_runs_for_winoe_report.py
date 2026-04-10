"""Expand evaluation runs for fit-profile reporting.

Revision ID: 202603120001
Revises: 202603110002
Create Date: 2026-03-12 09:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202603120001"
down_revision: str | Sequence[str] | None = "202603110002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "evaluation_runs", sa.Column("job_id", sa.String(length=36), nullable=True)
    )
    op.add_column(
        "evaluation_runs",
        sa.Column("basis_fingerprint", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "evaluation_runs",
        sa.Column("overall_fit_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "evaluation_runs",
        sa.Column("recommendation", sa.String(length=32), nullable=True),
    )
    op.add_column("evaluation_runs", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column(
        "evaluation_runs",
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "evaluation_runs", sa.Column("raw_report_json", sa.JSON(), nullable=True)
    )
    op.add_column(
        "evaluation_runs",
        sa.Column("error_code", sa.String(length=100), nullable=True),
    )

    op.create_index(
        "ix_evaluation_runs_candidate_session_status_started_at",
        "evaluation_runs",
        ["candidate_session_id", "status", "started_at"],
        unique=False,
    )
    op.create_index(
        "ix_evaluation_runs_job_id",
        "evaluation_runs",
        ["job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_evaluation_runs_job_id", table_name="evaluation_runs")
    op.drop_index(
        "ix_evaluation_runs_candidate_session_status_started_at",
        table_name="evaluation_runs",
    )

    op.drop_column("evaluation_runs", "error_code")
    op.drop_column("evaluation_runs", "raw_report_json")
    op.drop_column("evaluation_runs", "generated_at")
    op.drop_column("evaluation_runs", "confidence")
    op.drop_column("evaluation_runs", "recommendation")
    op.drop_column("evaluation_runs", "overall_fit_score")
    op.drop_column("evaluation_runs", "basis_fingerprint")
    op.drop_column("evaluation_runs", "job_id")
