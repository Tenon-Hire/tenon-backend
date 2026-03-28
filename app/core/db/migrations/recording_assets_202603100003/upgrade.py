"""Application module for upgrade workflows."""

from __future__ import annotations

from .constants import (
    CK_RECORDING_ASSETS_STATUS,
    CK_TRANSCRIPTS_STATUS,
    IX_RECORDING_ASSETS_SESSION_ID,
    IX_RECORDING_ASSETS_SESSION_TASK_CREATED,
    IX_RECORDING_ASSETS_TASK_ID,
    IX_TRANSCRIPTS_RECORDING_ID,
    IX_TRANSCRIPTS_STATUS_CREATED_AT,
    RECORDING_ASSETS_TABLE,
    TRANSCRIPTS_TABLE,
    UQ_RECORDING_ASSETS_STORAGE_KEY,
    UQ_TRANSCRIPTS_RECORDING_ID,
)


def run_upgrade(op, sa) -> None:
    """Run upgrade."""
    _create_recording_assets_table(op, sa)
    _create_transcripts_table(op, sa)


def _create_recording_assets_table(op, sa) -> None:
    op.create_table(
        RECORDING_ASSETS_TABLE,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_session_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("bytes", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="uploading"
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
        sa.UniqueConstraint("storage_key", name=UQ_RECORDING_ASSETS_STORAGE_KEY),
        sa.CheckConstraint(
            "status IN ('uploading','uploaded','processing','ready','failed')",
            name=CK_RECORDING_ASSETS_STATUS,
        ),
    )
    op.create_index(
        IX_RECORDING_ASSETS_SESSION_TASK_CREATED,
        RECORDING_ASSETS_TABLE,
        ["candidate_session_id", "task_id", "created_at"],
        unique=False,
    )
    op.create_index(
        IX_RECORDING_ASSETS_SESSION_ID,
        RECORDING_ASSETS_TABLE,
        ["candidate_session_id"],
        unique=False,
    )
    op.create_index(
        IX_RECORDING_ASSETS_TASK_ID,
        RECORDING_ASSETS_TABLE,
        ["task_id"],
        unique=False,
    )


def _create_transcripts_table(op, sa) -> None:
    op.create_table(
        TRANSCRIPTS_TABLE,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recording_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("segments_json", sa.JSON(), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="pending"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["recording_id"], [f"{RECORDING_ASSETS_TABLE}.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recording_id", name=UQ_TRANSCRIPTS_RECORDING_ID),
        sa.CheckConstraint(
            "status IN ('pending','processing','ready','failed')",
            name=CK_TRANSCRIPTS_STATUS,
        ),
    )
    op.create_index(
        IX_TRANSCRIPTS_RECORDING_ID,
        TRANSCRIPTS_TABLE,
        ["recording_id"],
        unique=False,
    )
    op.create_index(
        IX_TRANSCRIPTS_STATUS_CREATED_AT,
        TRANSCRIPTS_TABLE,
        ["status", "created_at"],
        unique=False,
    )
