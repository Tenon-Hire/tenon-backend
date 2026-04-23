"""Add structured reviewer sub-report persistence.

Revision ID: 202604180001
Revises: 202604170001
Create Date: 2026-04-18 00:01:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202604180001"
down_revision: str | Sequence[str] | None = "202604170001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evaluation_reviewer_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reviewer_agent_key",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column("day_index", sa.Integer(), nullable=False),
        sa.Column("submission_kind", sa.String(length=50), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("dimensional_scores_json", sa.JSON(), nullable=False),
        sa.Column("evidence_citations_json", sa.JSON(), nullable=False),
        sa.Column("assessment_text", sa.Text(), nullable=False),
        sa.Column("strengths_json", sa.JSON(), nullable=False),
        sa.Column("risks_json", sa.JSON(), nullable=False),
        sa.Column("raw_output_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "day_index BETWEEN 1 AND 5",
            name="ck_evaluation_reviewer_reports_day_index",
        ),
        sa.UniqueConstraint(
            "run_id",
            "reviewer_agent_key",
            "day_index",
            name="uq_evaluation_reviewer_reports_run_agent_day",
        ),
    )
    op.create_index(
        "ix_evaluation_reviewer_reports_run_id",
        "evaluation_reviewer_reports",
        ["run_id"],
    )
    op.create_index(
        "ix_evaluation_reviewer_reports_reviewer_agent_key",
        "evaluation_reviewer_reports",
        ["reviewer_agent_key"],
    )
    op.create_index(
        "ix_evaluation_reviewer_reports_day_index",
        "evaluation_reviewer_reports",
        ["day_index"],
    )
    op.create_index(
        "ix_evaluation_reviewer_reports_submission_kind",
        "evaluation_reviewer_reports",
        ["submission_kind"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_evaluation_reviewer_reports_submission_kind",
        table_name="evaluation_reviewer_reports",
    )
    op.drop_index(
        "ix_evaluation_reviewer_reports_day_index",
        table_name="evaluation_reviewer_reports",
    )
    op.drop_index(
        "ix_evaluation_reviewer_reports_reviewer_agent_key",
        table_name="evaluation_reviewer_reports",
    )
    op.drop_index(
        "ix_evaluation_reviewer_reports_run_id",
        table_name="evaluation_reviewer_reports",
    )
    op.drop_table("evaluation_reviewer_reports")

