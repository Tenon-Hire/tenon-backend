"""Add scenario_versions persistence and simulation active scenario pointer.

Revision ID: 202603090001
Revises: 202603080004
Create Date: 2026-03-09 00:01:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from app.core.db.migrations.scenario_versions_202603090001 import (
    run_downgrade,
    run_upgrade,
)

revision: str = "202603090001"
down_revision: str | Sequence[str] | None = "202603080004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    run_upgrade(op)


def downgrade() -> None:
    run_downgrade(op)
