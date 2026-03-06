"""Add task drafts table for candidate autosave.

Revision ID: 202603050002
Revises: 202603050001
Create Date: 2026-03-05 00:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202603050002"
down_revision: str | Sequence[str] | None = "202603050001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "task_drafts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_session_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("content_json", sa.JSON(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalized_submission_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["candidate_session_id"], ["candidate_sessions.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["finalized_submission_id"], ["submissions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "candidate_session_id",
            "task_id",
            name="uq_task_drafts_candidate_session_task",
        ),
    )

    op.create_index(
        "ix_task_drafts_candidate_session_id",
        "task_drafts",
        ["candidate_session_id"],
        unique=False,
    )
    op.create_index("ix_task_drafts_task_id", "task_drafts", ["task_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_task_drafts_task_id", table_name="task_drafts")
    op.drop_index("ix_task_drafts_candidate_session_id", table_name="task_drafts")
    op.drop_table("task_drafts")
