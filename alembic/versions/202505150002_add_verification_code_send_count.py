"""add verification code send count

Revision ID: 202505150002
Revises: 202505150001
Create Date: 2025-05-15 00:02:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "202505150002"
down_revision: Union[str, None] = "202505150001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "candidate_sessions",
        sa.Column(
            "verification_code_send_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("candidate_sessions", "verification_code_send_count")
