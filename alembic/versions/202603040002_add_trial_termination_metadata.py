"""Add optional simulation termination metadata fields.

Revision ID: 202603040002
Revises: 202603040001
Create Date: 2026-03-04 00:02:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202603040002"
down_revision: str | Sequence[str] | None = "202603040001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "simulations",
        sa.Column("terminated_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "simulations",
        sa.Column("terminated_by_recruiter_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_simulations_terminated_by_recruiter_id_users",
        "simulations",
        "users",
        ["terminated_by_recruiter_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_simulations_terminated_by_recruiter_id_users",
        "simulations",
        type_="foreignkey",
    )
    op.drop_column("simulations", "terminated_by_recruiter_id")
    op.drop_column("simulations", "terminated_reason")
