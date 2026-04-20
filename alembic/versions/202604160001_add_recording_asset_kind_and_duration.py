"""Add recording asset kind and duration metadata.

Revision ID: 202604160001
Revises: 202604150001
Create Date: 2026-04-16 10:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202604160001"
down_revision: str | Sequence[str] | None = "202604150001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("recording_assets") as batch_op:
        batch_op.add_column(
            sa.Column(
                "asset_kind",
                sa.String(length=50),
                nullable=False,
                server_default="recording",
            )
        )
        batch_op.add_column(sa.Column("duration_seconds", sa.Integer(), nullable=True))
        batch_op.create_index(
            "ix_recording_assets_candidate_session_task_kind",
            ["candidate_session_id", "task_id", "asset_kind"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("recording_assets") as batch_op:
        batch_op.drop_index("ix_recording_assets_candidate_session_task_kind")
        batch_op.drop_column("duration_seconds")
        batch_op.drop_column("asset_kind")
