"""Backfill legacy scenario-version AI policy snapshots.

Revision ID: 202604010002
Revises: 202604010001
Create Date: 2026-04-01 00:20:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from app.core.db.migrations.ai_policy_snapshots_202604010002 import run_upgrade

revision: str = "202604010002"
down_revision: str | Sequence[str] | None = "202604010001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from alembic import op

    run_upgrade(op.get_bind())


def downgrade() -> None:
    # Backfill migration is intentionally irreversible.
    pass
