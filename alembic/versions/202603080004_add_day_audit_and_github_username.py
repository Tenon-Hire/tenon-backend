"""Add day cutoff audit table and candidate GitHub username.

Revision ID: 202603080004
Revises: 202603080003
Create Date: 2026-03-08 16:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202603080004"
down_revision: str | Sequence[str] | None = "202603080003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "candidate_sessions",
        sa.Column("github_username", sa.String(length=39), nullable=True),
    )
    op.create_table(
        "candidate_day_audits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_session_id", sa.Integer(), nullable=False),
        sa.Column("day_index", sa.Integer(), nullable=False),
        sa.Column("cutoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cutoff_commit_sha", sa.String(length=100), nullable=False),
        sa.Column("eval_basis_ref", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "day_index IN (2, 3)", name="ck_candidate_day_audits_day_index"
        ),
        sa.ForeignKeyConstraint(
            ["candidate_session_id"],
            ["candidate_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "candidate_session_id",
            "day_index",
            name="uq_candidate_day_audits_session_day",
        ),
    )
    op.create_index(
        "ix_candidate_day_audits_candidate_session_day",
        "candidate_day_audits",
        ["candidate_session_id", "day_index"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_candidate_day_audits_candidate_session_day",
        table_name="candidate_day_audits",
    )
    op.drop_table("candidate_day_audits")
    op.drop_column("candidate_sessions", "github_username")
