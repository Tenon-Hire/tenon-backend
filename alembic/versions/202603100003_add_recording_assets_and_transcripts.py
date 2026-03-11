"""Add recording assets and transcripts tables.

Revision ID: 202603100003
Revises: 202603100002
Create Date: 2026-03-10 20:10:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202603100003"
down_revision: str | Sequence[str] | None = "202603100002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recording_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_session_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("bytes", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="uploading",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["candidate_session_id"], ["candidate_sessions.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key", name="uq_recording_assets_storage_key"),
        sa.CheckConstraint(
            "status IN ('uploading','uploaded','processing','ready','failed')",
            name="ck_recording_assets_status",
        ),
    )
    op.create_index(
        "ix_recording_assets_candidate_session_task_created_at",
        "recording_assets",
        ["candidate_session_id", "task_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_recording_assets_candidate_session_id",
        "recording_assets",
        ["candidate_session_id"],
        unique=False,
    )
    op.create_index(
        "ix_recording_assets_task_id",
        "recording_assets",
        ["task_id"],
        unique=False,
    )

    op.create_table(
        "transcripts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recording_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("segments_json", sa.JSON(), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["recording_id"], ["recording_assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recording_id", name="uq_transcripts_recording_id"),
        sa.CheckConstraint(
            "status IN ('pending','processing','ready','failed')",
            name="ck_transcripts_status",
        ),
    )
    op.create_index(
        "ix_transcripts_recording_id",
        "transcripts",
        ["recording_id"],
        unique=False,
    )
    op.create_index(
        "ix_transcripts_status_created_at",
        "transcripts",
        ["status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_transcripts_status_created_at", table_name="transcripts")
    op.drop_index("ix_transcripts_recording_id", table_name="transcripts")
    op.drop_table("transcripts")

    op.drop_index("ix_recording_assets_task_id", table_name="recording_assets")
    op.drop_index(
        "ix_recording_assets_candidate_session_id",
        table_name="recording_assets",
    )
    op.drop_index(
        "ix_recording_assets_candidate_session_task_created_at",
        table_name="recording_assets",
    )
    op.drop_table("recording_assets")

