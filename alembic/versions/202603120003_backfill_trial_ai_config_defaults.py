"""Backfill simulation AI config defaults and enforce non-null columns.

Revision ID: 202603120003
Revises: 202603120002
Create Date: 2026-03-12 00:03:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202603120003"
down_revision: str | Sequence[str] | None = "202603120002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_AI_NOTICE_VERSION = "mvp1"
DEFAULT_AI_NOTICE_TEXT = (
    "We use AI to help evaluate submitted work artifacts, coding outputs, and "
    "communication signals across the simulation. Human reviewers oversee "
    "AI-generated findings and final hiring decisions are made by people."
)
DEFAULT_AI_EVAL_ENABLED_BY_DAY = {
    "1": True,
    "2": True,
    "3": True,
    "4": True,
    "5": True,
}
DEFAULT_AI_EVAL_ENABLED_BY_DAY_JSON = (
    '{"1": true, "2": true, "3": true, "4": true, "5": true}'
)


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE simulations
            SET ai_notice_version = :default_notice_version
            WHERE ai_notice_version IS NULL OR TRIM(ai_notice_version) = ''
            """
        ).bindparams(default_notice_version=DEFAULT_AI_NOTICE_VERSION)
    )
    op.execute(
        sa.text(
            """
            UPDATE simulations
            SET ai_notice_text = :default_notice_text
            WHERE ai_notice_text IS NULL OR TRIM(ai_notice_text) = ''
            """
        ).bindparams(default_notice_text=DEFAULT_AI_NOTICE_TEXT)
    )
    op.execute(
        sa.text(
            """
            UPDATE simulations
            SET ai_eval_enabled_by_day = :default_eval_enabled_by_day
            WHERE ai_eval_enabled_by_day IS NULL
            """
        ).bindparams(
            sa.bindparam(
                "default_eval_enabled_by_day",
                value=DEFAULT_AI_EVAL_ENABLED_BY_DAY,
                type_=sa.JSON(),
            )
        )
    )

    op.alter_column(
        "simulations",
        "ai_notice_version",
        existing_type=sa.String(length=100),
        nullable=False,
        server_default=DEFAULT_AI_NOTICE_VERSION,
    )
    op.alter_column(
        "simulations",
        "ai_notice_text",
        existing_type=sa.Text(),
        nullable=False,
        server_default=DEFAULT_AI_NOTICE_TEXT,
    )
    op.alter_column(
        "simulations",
        "ai_eval_enabled_by_day",
        existing_type=sa.JSON(),
        nullable=False,
        server_default=sa.text(f"'{DEFAULT_AI_EVAL_ENABLED_BY_DAY_JSON}'"),
    )


def downgrade() -> None:
    op.alter_column(
        "simulations",
        "ai_eval_enabled_by_day",
        existing_type=sa.JSON(),
        nullable=True,
        server_default=None,
    )
    op.alter_column(
        "simulations",
        "ai_notice_text",
        existing_type=sa.Text(),
        nullable=True,
        server_default=None,
    )
    op.alter_column(
        "simulations",
        "ai_notice_version",
        existing_type=sa.String(length=100),
        nullable=True,
        server_default=None,
    )
