"""Make workspace template repo columns nullable for from-scratch bootstrap.

Revision ID: 202604150001
Revises: 202604140001
Create Date: 2026-04-15 00:01:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202604150001"
down_revision: str | Sequence[str] | None = "202604140001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("workspace_groups") as batch_op:
        batch_op.alter_column(
            "template_repo_full_name",
            existing_type=sa.String(length=255),
            existing_nullable=False,
            nullable=True,
        )
    with op.batch_alter_table("workspaces") as batch_op:
        batch_op.alter_column(
            "template_repo_full_name",
            existing_type=sa.String(length=255),
            existing_nullable=False,
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("workspace_groups") as batch_op:
        batch_op.alter_column(
            "template_repo_full_name",
            existing_type=sa.String(length=255),
            existing_nullable=True,
            nullable=False,
        )
    with op.batch_alter_table("workspaces") as batch_op:
        batch_op.alter_column(
            "template_repo_full_name",
            existing_type=sa.String(length=255),
            existing_nullable=True,
            nullable=False,
        )
