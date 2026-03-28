"""Add simulation lifecycle state machine columns and backfill status.

Revision ID: 202603030002
Revises: 202603030001
Create Date: 2026-03-03 00:02:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202603030002"
down_revision: str | Sequence[str] | None = "202603030001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SIMULATION_STATUS_CHECK_NAME = "ck_simulations_status_lifecycle"
# Must match SIMULATION_STATUSES in app/simulations/repositories/*_simulation_model.py.
_SIMULATION_STATUS_CHECK_EXPR = (
    "status IN ('draft','generating','ready_for_review','active_inviting','terminated')"
)


def upgrade() -> None:
    op.add_column(
        "simulations",
        sa.Column("generating_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "simulations",
        sa.Column("ready_for_review_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "simulations",
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "simulations",
        sa.Column("terminated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Existing simulations were invitable before lifecycle enforcement.
    op.execute(
        sa.text(
            """
            UPDATE simulations
            SET status = 'active_inviting',
                activated_at = COALESCE(activated_at, created_at, CURRENT_TIMESTAMP)
            """
        )
    )

    op.alter_column(
        "simulations",
        "status",
        existing_type=sa.String(length=50),
        nullable=False,
        server_default=sa.text("'generating'"),
    )
    op.create_check_constraint(
        _SIMULATION_STATUS_CHECK_NAME,
        "simulations",
        _SIMULATION_STATUS_CHECK_EXPR,
    )


def downgrade() -> None:
    op.drop_constraint(_SIMULATION_STATUS_CHECK_NAME, "simulations", type_="check")
    op.alter_column(
        "simulations",
        "status",
        existing_type=sa.String(length=50),
        nullable=True,
        server_default=None,
    )
    op.drop_column("simulations", "terminated_at")
    op.drop_column("simulations", "activated_at")
    op.drop_column("simulations", "ready_for_review_at")
    op.drop_column("simulations", "generating_at")
