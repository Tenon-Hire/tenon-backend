"""Add workspace cleanup and access revocation state columns.

Revision ID: 202603130002
Revises: 202603130001
Create Date: 2026-03-13 00:02:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202603130002"
down_revision: str | Sequence[str] | None = "202603130001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column("cleanup_status", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "workspaces",
        sa.Column("cleanup_attempted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "workspaces",
        sa.Column("cleaned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "workspaces",
        sa.Column("cleanup_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "workspaces",
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "workspaces",
        sa.Column("access_revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "workspaces",
        sa.Column("access_revocation_error", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_workspaces_cleanup_status",
        "workspaces",
        ["cleanup_status"],
        unique=False,
    )
    op.create_index(
        "ix_workspaces_retention_expires_at",
        "workspaces",
        ["retention_expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_workspaces_retention_expires_at", table_name="workspaces")
    op.drop_index("ix_workspaces_cleanup_status", table_name="workspaces")
    op.drop_column("workspaces", "access_revocation_error")
    op.drop_column("workspaces", "access_revoked_at")
    op.drop_column("workspaces", "retention_expires_at")
    op.drop_column("workspaces", "cleanup_error")
    op.drop_column("workspaces", "cleaned_at")
    op.drop_column("workspaces", "cleanup_attempted_at")
    op.drop_column("workspaces", "cleanup_status")
