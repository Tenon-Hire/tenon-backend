"""Add media retention purge metadata and audits.

Revision ID: 202604200001
Revises: 202604190001
Create Date: 2026-04-20 00:01:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202604200001"
down_revision: str | Sequence[str] | None = "202604190001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _backfill_retention_expires_at() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        bind.execute(
            sa.text(
                """
                UPDATE recording_assets
                SET retention_expires_at = created_at + INTERVAL '30 days'
                WHERE retention_expires_at IS NULL
                """
            )
        )
    elif dialect == "sqlite":
        bind.execute(
            sa.text(
                """
                UPDATE recording_assets
                SET retention_expires_at = datetime(created_at, '+30 days')
                WHERE retention_expires_at IS NULL
                """
            )
        )
    else:
        bind.execute(
            sa.text(
                """
                UPDATE recording_assets
                SET retention_expires_at = created_at
                WHERE retention_expires_at IS NULL
                """
            )
        )


def upgrade() -> None:
    with op.batch_alter_table("recording_assets") as batch_op:
        batch_op.add_column(
            sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("purge_reason", sa.String(length=50), nullable=True)
        )
        batch_op.add_column(
            sa.Column("purge_status", sa.String(length=50), nullable=True)
        )
        batch_op.create_index(
            "ix_recording_assets_retention_expires_purged",
            ["retention_expires_at", "purged_at"],
            unique=False,
        )

    _backfill_retention_expires_at()

    op.create_table(
        "media_purge_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("media_id", sa.Integer(), nullable=False),
        sa.Column("candidate_session_id", sa.Integer(), nullable=True),
        sa.Column("trial_id", sa.Integer(), nullable=True),
        sa.Column("candidate_user_id", sa.Integer(), nullable=True),
        sa.Column("actor_type", sa.String(length=50), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=True),
        sa.Column("purge_reason", sa.String(length=50), nullable=False),
        sa.Column("outcome", sa.String(length=50), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_media_purge_audits_media_created_at",
        "media_purge_audits",
        ["media_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_media_purge_audits_reason_created_at",
        "media_purge_audits",
        ["purge_reason", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_media_purge_audits_candidate_session_created_at",
        "media_purge_audits",
        ["candidate_session_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_media_purge_audits_candidate_session_created_at",
        table_name="media_purge_audits",
    )
    op.drop_index(
        "ix_media_purge_audits_reason_created_at",
        table_name="media_purge_audits",
    )
    op.drop_index(
        "ix_media_purge_audits_media_created_at",
        table_name="media_purge_audits",
    )
    op.drop_table("media_purge_audits")

    with op.batch_alter_table("recording_assets") as batch_op:
        batch_op.drop_index("ix_recording_assets_retention_expires_purged")
        batch_op.drop_column("purge_status")
        batch_op.drop_column("purge_reason")
        batch_op.drop_column("retention_expires_at")
