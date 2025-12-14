"""add-code_blob-unique-constraint-for-submissions

Revision ID: b5e134bdb971
Revises: 174928546828
Create Date: 2025-12-14 15:02:39.333038

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b5e134bdb971'
down_revision: Union[str, Sequence[str], None] = '174928546828'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("submissions", sa.Column("code_blob", sa.Text(), nullable=True))
    op.create_unique_constraint(
        "uq_submissions_candidate_session_task",
        "submissions",
        ["candidate_session_id", "task_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_submissions_candidate_session_task",
        "submissions",
        type_="unique",
    )
    op.drop_column("submissions", "code_blob")