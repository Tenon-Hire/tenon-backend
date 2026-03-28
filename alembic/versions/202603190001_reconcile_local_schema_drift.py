"""Reconcile schema drift for locally stamped databases.

Revision ID: 202603190001
Revises: 202603150002
Create Date: 2026-03-19 00:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from app.core.db.migrations.reconcile_202603190001 import run_upgrade

revision: str = "202603190001"
down_revision: str | Sequence[str] | None = "202603150002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    run_upgrade(op, op.get_bind())


def downgrade() -> None:
    # This reconciliation migration is intentionally non-reversible.
    pass
