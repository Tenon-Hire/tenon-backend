"""Add frozen AI policy snapshots to scenario versions.

Revision ID: 202604010001
Revises: 202603310001
Create Date: 2026-04-01 00:01:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202604010001"
down_revision: str | Sequence[str] | None = "202603310001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scenario_versions",
        sa.Column("ai_policy_snapshot_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scenario_versions", "ai_policy_snapshot_json")
