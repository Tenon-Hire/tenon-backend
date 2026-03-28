"""Remove candidate OTP fields and legacy access tokens.

Revision ID: 202506150001
Revises: 202506010001
Create Date: 2025-06-15 00:00:01.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.db.migrations.candidate_otp_202506150001 import (
    run_downgrade,
    run_upgrade,
)


revision: str = "202506150001"
down_revision: Union[str, Sequence[str], None] = "202506010001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    run_upgrade(op, sa)


def downgrade() -> None:
    run_downgrade(op, sa)
