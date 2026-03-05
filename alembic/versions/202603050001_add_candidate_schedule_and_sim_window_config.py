"""Add candidate scheduling fields and simulation day window config.

Revision ID: 202603050001
Revises: 202603040002
Create Date: 2026-03-05 00:01:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202603050001"
down_revision: str | Sequence[str] | None = "202603040002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "candidate_sessions",
        sa.Column("scheduled_start_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "candidate_sessions",
        sa.Column("candidate_timezone", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "candidate_sessions",
        sa.Column("day_windows_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "candidate_sessions",
        sa.Column("schedule_locked_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "simulations",
        sa.Column(
            "day_window_start_local",
            sa.Time(),
            nullable=False,
            server_default=sa.text("'09:00:00'"),
        ),
    )
    op.add_column(
        "simulations",
        sa.Column(
            "day_window_end_local",
            sa.Time(),
            nullable=False,
            server_default=sa.text("'17:00:00'"),
        ),
    )
    op.add_column(
        "simulations",
        sa.Column(
            "day_window_overrides_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "simulations",
        sa.Column("day_window_overrides_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("simulations", "day_window_overrides_json")
    op.drop_column("simulations", "day_window_overrides_enabled")
    op.drop_column("simulations", "day_window_end_local")
    op.drop_column("simulations", "day_window_start_local")

    op.drop_column("candidate_sessions", "schedule_locked_at")
    op.drop_column("candidate_sessions", "day_windows_json")
    op.drop_column("candidate_sessions", "candidate_timezone")
    op.drop_column("candidate_sessions", "scheduled_start_at")
