"""Add admin action audit table for demo-ops endpoints.

Revision ID: 202603150001
Revises: 202603130003
Create Date: 2026-03-15 00:01:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202603150001"
down_revision: str | Sequence[str] | None = "202603130003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_action_audits",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("actor_type", sa.String(length=50), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=100), nullable=False),
        sa.Column("target_id", sa.String(length=100), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_action_audits_created_at",
        "admin_action_audits",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_admin_action_audits_action_created_at",
        "admin_action_audits",
        ["action", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_admin_action_audits_action_created_at",
        table_name="admin_action_audits",
    )
    op.drop_index(
        "ix_admin_action_audits_created_at",
        table_name="admin_action_audits",
    )
    op.drop_table("admin_action_audits")
