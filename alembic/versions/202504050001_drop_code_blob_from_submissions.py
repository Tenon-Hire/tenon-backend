"""Remove unused code_blob column from submissions.

Revision ID: 202504050001
Revises: 202503200001
Create Date: 2025-04-05 00:00:01.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202504050001"
down_revision: Union[str, Sequence[str], None] = "202503200001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("submissions", "code_blob")


def downgrade() -> None:
    op.add_column("submissions", sa.Column("code_blob", sa.Text(), nullable=True))
