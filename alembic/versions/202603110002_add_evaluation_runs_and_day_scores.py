"""Add evaluation runs and day scores persistence tables.

Revision ID: 202603110002
Revises: 202603110001
Create Date: 2026-03-11 13:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from app.core.db.migrations.evaluation_runs_202603110002 import (
    run_downgrade,
    run_upgrade,
)

revision: str = "202603110002"
down_revision: str | Sequence[str] | None = "202603110001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from alembic import op
    import sqlalchemy as sa

    run_upgrade(op, sa)


def downgrade() -> None:
    from alembic import op

    run_downgrade(op)
