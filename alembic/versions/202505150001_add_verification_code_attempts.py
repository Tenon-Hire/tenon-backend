"""add verification code attempts

Revision ID: 202505150001
Revises: 202505050003
Create Date: 2025-05-15 00:01:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "202505150001"
down_revision: Union[str, None] = "202505050003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "candidate_sessions",
        sa.Column(
            "verification_code_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("candidate_sessions", "verification_code_attempts")
