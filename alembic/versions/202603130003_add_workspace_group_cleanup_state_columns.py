"""Add workspace group cleanup/access revocation lifecycle state columns.

Revision ID: 202603130003
Revises: 202603130002
Create Date: 2026-03-13 00:03:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202603130003"
down_revision: str | Sequence[str] | None = "202603130002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workspace_groups",
        sa.Column("cleanup_status", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "workspace_groups",
        sa.Column("cleanup_attempted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "workspace_groups",
        sa.Column("cleaned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "workspace_groups",
        sa.Column("cleanup_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "workspace_groups",
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "workspace_groups",
        sa.Column("access_revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "workspace_groups",
        sa.Column("access_revocation_error", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_workspace_groups_cleanup_status",
        "workspace_groups",
        ["cleanup_status"],
        unique=False,
    )
    op.create_index(
        "ix_workspace_groups_retention_expires_at",
        "workspace_groups",
        ["retention_expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workspace_groups_retention_expires_at",
        table_name="workspace_groups",
    )
    op.drop_index(
        "ix_workspace_groups_cleanup_status",
        table_name="workspace_groups",
    )
    op.drop_column("workspace_groups", "access_revocation_error")
    op.drop_column("workspace_groups", "access_revoked_at")
    op.drop_column("workspace_groups", "retention_expires_at")
    op.drop_column("workspace_groups", "cleanup_error")
    op.drop_column("workspace_groups", "cleaned_at")
    op.drop_column("workspace_groups", "cleanup_attempted_at")
    op.drop_column("workspace_groups", "cleanup_status")
