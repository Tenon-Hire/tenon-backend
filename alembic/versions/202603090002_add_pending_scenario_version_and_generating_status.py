"""Add simulation pending scenario pointer and generating scenario status.

Revision ID: 202603090002
Revises: 202603090001
Create Date: 2026-03-09 18:05:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202603090002"
down_revision: str | Sequence[str] | None = "202603090001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCENARIO_STATUS_CHECK_NAME = "ck_scenario_versions_status"
_SCENARIO_STATUS_CHECK_WITH_GENERATING = (
    "status IN ('draft','generating','ready','locked')"
)
_SCENARIO_STATUS_CHECK_WITHOUT_GENERATING = "status IN ('draft','ready','locked')"


def upgrade() -> None:
    with op.batch_alter_table("scenario_versions") as batch_op:
        batch_op.drop_constraint(_SCENARIO_STATUS_CHECK_NAME, type_="check")
        batch_op.create_check_constraint(
            _SCENARIO_STATUS_CHECK_NAME,
            _SCENARIO_STATUS_CHECK_WITH_GENERATING,
        )

    op.add_column(
        "simulations",
        sa.Column("pending_scenario_version_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_simulations_pending_scenario_version_id",
        "simulations",
        "scenario_versions",
        ["pending_scenario_version_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_simulations_pending_scenario_version_id",
        "simulations",
        type_="foreignkey",
    )
    op.drop_column("simulations", "pending_scenario_version_id")

    with op.batch_alter_table("scenario_versions") as batch_op:
        batch_op.drop_constraint(_SCENARIO_STATUS_CHECK_NAME, type_="check")
        batch_op.create_check_constraint(
            _SCENARIO_STATUS_CHECK_NAME,
            _SCENARIO_STATUS_CHECK_WITHOUT_GENERATING,
        )

