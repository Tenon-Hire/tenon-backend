"""Add last_run_at to submissions

Revision ID: 3d7f8c5b6b8c
Revises: fa61fe2e7edd
Create Date: 2025-12-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3d7f8c5b6b8c"
down_revision: Union[str, Sequence[str], None] = "fa61fe2e7edd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "submissions",
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("submissions", "last_run_at")
