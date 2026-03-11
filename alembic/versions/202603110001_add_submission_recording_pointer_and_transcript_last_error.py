"""Add submission recording pointer and transcript error details.

Revision ID: 202603110001
Revises: 202603100003
Create Date: 2026-03-11 09:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202603110001"
down_revision: str | Sequence[str] | None = "202603100003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_SUBMISSIONS_RECORDING_FK = "fk_submissions_recording_id_recording_assets"


def upgrade() -> None:
    with op.batch_alter_table("submissions") as batch_op:
        batch_op.add_column(sa.Column("recording_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            "ix_submissions_recording_id",
            ["recording_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            _SUBMISSIONS_RECORDING_FK,
            "recording_assets",
            ["recording_id"],
            ["id"],
        )

    with op.batch_alter_table("transcripts") as batch_op:
        batch_op.add_column(sa.Column("last_error", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("transcripts") as batch_op:
        batch_op.drop_column("last_error")

    with op.batch_alter_table("submissions") as batch_op:
        batch_op.drop_constraint(_SUBMISSIONS_RECORDING_FK, type_="foreignkey")
        batch_op.drop_index("ix_submissions_recording_id")
        batch_op.drop_column("recording_id")
