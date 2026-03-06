"""Add content_json column to submissions.

Revision ID: 202603050003
Revises: 202603050002
Create Date: 2026-03-05 00:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202603050003"
down_revision: str | Sequence[str] | None = "202603050002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("submissions", sa.Column("content_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("submissions", "content_json")
