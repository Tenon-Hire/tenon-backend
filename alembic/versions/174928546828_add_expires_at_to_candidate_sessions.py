"""add expires_at to candidate_sessions

Revision ID: 174928546828
Revises: 7dea06d20deb
Create Date: 2025-12-14 12:16:09.765797

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '174928546828'
down_revision: Union[str, Sequence[str], None] = '7dea06d20deb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "candidate_sessions",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("candidate_sessions", "expires_at")