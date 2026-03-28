"""Add recording assets and transcripts tables.

Revision ID: 202603100003
Revises: 202603100002
Create Date: 2026-03-10 20:10:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from app.core.db.migrations.recording_assets_202603100003 import (
    run_downgrade,
    run_upgrade,
)

revision: str = "202603100003"
down_revision: str | Sequence[str] | None = "202603100002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from alembic import op
    import sqlalchemy as sa

    run_upgrade(op, sa)


def downgrade() -> None:
    from alembic import op

    run_downgrade(op)
