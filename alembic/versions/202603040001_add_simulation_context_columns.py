"""Add recruiter context and AI toggle columns to simulations.

Revision ID: 202603040001
Revises: 202603030002
Create Date: 2026-03-04 00:01:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202603040001"
down_revision: str | Sequence[str] | None = "202603030002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "simulations",
        sa.Column("company_context", sa.JSON(), nullable=True),
    )
    op.add_column(
        "simulations",
        sa.Column("ai_notice_version", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "simulations",
        sa.Column("ai_notice_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "simulations",
        sa.Column("ai_eval_enabled_by_day", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("simulations", "ai_eval_enabled_by_day")
    op.drop_column("simulations", "ai_notice_text")
    op.drop_column("simulations", "ai_notice_version")
    op.drop_column("simulations", "company_context")
