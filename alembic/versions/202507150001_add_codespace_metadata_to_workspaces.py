"""Add codespace metadata to workspaces

Revision ID: 202507150001
Revises: 202507010001
Create Date: 2025-07-15 00:00:01.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202507150001"
down_revision: Union[str, Sequence[str], None] = "202507010001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column("codespace_name", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "workspaces",
        sa.Column("codespace_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "workspaces",
        sa.Column("codespace_state", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workspaces", "codespace_state")
    op.drop_column("workspaces", "codespace_url")
    op.drop_column("workspaces", "codespace_name")
