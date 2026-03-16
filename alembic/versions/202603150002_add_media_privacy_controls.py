"""Add media privacy controls for consent, deletion, and retention.

Revision ID: 202603150002
Revises: 202603150001
Create Date: 2026-03-15 00:20:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202603150002"
down_revision: str | Sequence[str] | None = "202603150001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_RECORDING_STATUS_CONSTRAINT = "ck_recording_assets_status"


def upgrade() -> None:
    with op.batch_alter_table("candidate_sessions") as batch_op:
        batch_op.add_column(sa.Column("consent_version", sa.String(length=100), nullable=True))
        batch_op.add_column(
            sa.Column("consent_timestamp", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("ai_notice_version", sa.String(length=100), nullable=True))

    with op.batch_alter_table("recording_assets") as batch_op:
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("consent_version", sa.String(length=100), nullable=True))
        batch_op.add_column(
            sa.Column("consent_timestamp", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("ai_notice_version", sa.String(length=100), nullable=True))
        batch_op.drop_constraint(_RECORDING_STATUS_CONSTRAINT, type_="check")
        batch_op.create_check_constraint(
            _RECORDING_STATUS_CONSTRAINT,
            "status IN ('uploading','uploaded','processing','ready','failed','deleted','purged')",
        )
        batch_op.create_index(
            "ix_recording_assets_deleted_at",
            ["deleted_at"],
            unique=False,
        )
        batch_op.create_index(
            "ix_recording_assets_purged_at",
            ["purged_at"],
            unique=False,
        )

    with op.batch_alter_table("transcripts") as batch_op:
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_transcripts_deleted_at", ["deleted_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("transcripts") as batch_op:
        batch_op.drop_index("ix_transcripts_deleted_at")
        batch_op.drop_column("deleted_at")

    with op.batch_alter_table("recording_assets") as batch_op:
        batch_op.drop_index("ix_recording_assets_purged_at")
        batch_op.drop_index("ix_recording_assets_deleted_at")
        batch_op.drop_constraint(_RECORDING_STATUS_CONSTRAINT, type_="check")
        batch_op.create_check_constraint(
            _RECORDING_STATUS_CONSTRAINT,
            "status IN ('uploading','uploaded','processing','ready','failed')",
        )
        batch_op.drop_column("ai_notice_version")
        batch_op.drop_column("consent_timestamp")
        batch_op.drop_column("consent_version")
        batch_op.drop_column("purged_at")
        batch_op.drop_column("deleted_at")

    with op.batch_alter_table("candidate_sessions") as batch_op:
        batch_op.drop_column("ai_notice_version")
        batch_op.drop_column("consent_timestamp")
        batch_op.drop_column("consent_version")
