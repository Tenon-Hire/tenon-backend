"""Add AI runtime hookup columns and precommit bundle provenance.

Revision ID: 202603310001
Revises: 202603190001
Create Date: 2026-03-31 00:01:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202603310001"
down_revision: str | Sequence[str] | None = "202603190001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_PRECOMMIT_STATUS_CHECK = "status IN ('draft','ready','disabled')"
_NEW_PRECOMMIT_STATUS_CHECK = "status IN ('generating','ready','failed','disabled')"
_OLD_PRECOMMIT_CONTENT_CHECK = "(patch_text IS NOT NULL) OR (storage_ref IS NOT NULL)"
_NEW_PRECOMMIT_CONTENT_CHECK = (
    "(status != 'ready') OR (patch_text IS NOT NULL) OR (storage_ref IS NOT NULL)"
)


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("ai_prompt_overrides_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "simulations",
        sa.Column("ai_prompt_overrides_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "scenario_versions",
        sa.Column("codespace_spec_json", sa.JSON(), nullable=True),
    )

    op.execute(
        sa.text(
            """
            UPDATE precommit_bundles
            SET status = 'generating'
            WHERE status = 'draft'
            """
        )
    )

    with op.batch_alter_table("precommit_bundles") as batch_op:
        batch_op.alter_column(
            "content_sha256",
            existing_type=sa.String(length=64),
            nullable=True,
        )
        batch_op.add_column(sa.Column("commit_message", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("model_name", sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column("model_version", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("prompt_version", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(sa.Column("test_summary_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("provenance_json", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("last_error", sa.Text(), nullable=True))
        batch_op.drop_constraint("ck_precommit_bundles_status", type_="check")
        batch_op.create_check_constraint(
            "ck_precommit_bundles_status",
            _NEW_PRECOMMIT_STATUS_CHECK,
        )
        batch_op.drop_constraint("ck_precommit_bundle_content_source", type_="check")
        batch_op.create_check_constraint(
            "ck_precommit_bundle_content_source",
            _NEW_PRECOMMIT_CONTENT_CHECK,
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE precommit_bundles
            SET status = CASE
                WHEN status = 'generating' THEN 'draft'
                WHEN status = 'failed' THEN 'disabled'
                ELSE status
            END
            """
        )
    )

    with op.batch_alter_table("precommit_bundles") as batch_op:
        batch_op.drop_constraint("ck_precommit_bundles_status", type_="check")
        batch_op.create_check_constraint(
            "ck_precommit_bundles_status",
            _OLD_PRECOMMIT_STATUS_CHECK,
        )
        batch_op.drop_constraint("ck_precommit_bundle_content_source", type_="check")
        batch_op.create_check_constraint(
            "ck_precommit_bundle_content_source",
            _OLD_PRECOMMIT_CONTENT_CHECK,
        )
        batch_op.drop_column("last_error")
        batch_op.drop_column("provenance_json")
        batch_op.drop_column("test_summary_json")
        batch_op.drop_column("prompt_version")
        batch_op.drop_column("model_version")
        batch_op.drop_column("model_name")
        batch_op.drop_column("commit_message")
        batch_op.alter_column(
            "content_sha256",
            existing_type=sa.String(length=64),
            nullable=False,
        )

    op.drop_column("scenario_versions", "codespace_spec_json")
    op.drop_column("simulations", "ai_prompt_overrides_json")
    op.drop_column("companies", "ai_prompt_overrides_json")
