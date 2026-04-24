"""Add immutable Winoe rubric snapshots and trial rubric attachments.

Revision ID: 202604190001
Revises: 202604180001
Create Date: 2026-04-19 00:01:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202604190001"
down_revision: str | Sequence[str] | None = "202604180001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "trials",
        sa.Column("company_rubric_json", sa.JSON(), nullable=True),
    )
    op.create_table(
        "winoe_rubric_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "scenario_version_id",
            sa.Integer(),
            sa.ForeignKey("scenario_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("rubric_kind", sa.String(length=100), nullable=False),
        sa.Column("rubric_key", sa.String(length=100), nullable=False),
        sa.Column("rubric_version", sa.String(length=255), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("source_path", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "scope IN ('winoe','company')",
            name="ck_winoe_rubric_snapshots_scope",
        ),
        sa.UniqueConstraint(
            "scenario_version_id",
            "scope",
            "rubric_kind",
            "rubric_key",
            "rubric_version",
            name="uq_winoe_rubric_snapshots_scenario_scope_kind_key_version",
        ),
    )
    op.create_index(
        "ix_winoe_rubric_snapshots_scenario_version_id",
        "winoe_rubric_snapshots",
        ["scenario_version_id"],
    )
    op.create_index(
        "ix_winoe_rubric_snapshots_scope",
        "winoe_rubric_snapshots",
        ["scope"],
    )
    op.create_index(
        "ix_winoe_rubric_snapshots_rubric_kind",
        "winoe_rubric_snapshots",
        ["rubric_kind"],
    )
    op.create_index(
        "ix_winoe_rubric_snapshots_rubric_key",
        "winoe_rubric_snapshots",
        ["rubric_key"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_winoe_rubric_snapshots_rubric_key",
        table_name="winoe_rubric_snapshots",
    )
    op.drop_index(
        "ix_winoe_rubric_snapshots_rubric_kind",
        table_name="winoe_rubric_snapshots",
    )
    op.drop_index("ix_winoe_rubric_snapshots_scope", table_name="winoe_rubric_snapshots")
    op.drop_index(
        "ix_winoe_rubric_snapshots_scenario_version_id",
        table_name="winoe_rubric_snapshots",
    )
    op.drop_table("winoe_rubric_snapshots")
    op.drop_column("trials", "company_rubric_json")

