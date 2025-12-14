"""add candidate_name to candidate_sessions

Revision ID: 7dea06d20deb
Revises: 229e1ede13cc
Create Date: 2025-12-14 10:37:42.218422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '7dea06d20deb'
down_revision: Union[str, Sequence[str], None] = '229e1ede13cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "candidate_sessions",
        sa.Column("candidate_name", sa.String(length=255), nullable=False, server_default=""),
    )
    op.alter_column("candidate_sessions", "candidate_name", server_default=None)


def downgrade() -> None:
    op.drop_column("candidate_sessions", "candidate_name")