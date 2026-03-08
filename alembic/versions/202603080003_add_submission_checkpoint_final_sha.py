"""Add checkpoint/final SHA evidence columns to submissions.

Revision ID: 202603080003
Revises: 202603080002
Create Date: 2026-03-08 00:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202603080003"
down_revision: str | Sequence[str] | None = "202603080002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "submissions",
        sa.Column("checkpoint_sha", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "submissions",
        sa.Column("final_sha", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("submissions", "final_sha")
    op.drop_column("submissions", "checkpoint_sha")
