"""Schema operations for scenario_versions migration."""

from __future__ import annotations

import sqlalchemy as sa

from app.core.db.migrations.shared_trial_schema_compat import (
    resolve_trial_parent_table_name,
)

from .constants import (
    TRIAL_ACTIVE_SCENARIO_REQUIRED_CHECK_EXPR,
    TRIAL_ACTIVE_SCENARIO_REQUIRED_CHECK_NAME,
)


def _parent_table_name(op: object) -> str:
    return resolve_trial_parent_table_name(op.get_bind())


def create_schema(op: object) -> None:
    """Create schema."""
    parent_table_name = _parent_table_name(op)
    op.create_table(
        "scenario_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trial_id", sa.Integer(), nullable=False),
        sa.Column("version_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("storyline_md", sa.Text(), nullable=False),
        sa.Column("task_prompts_json", sa.JSON(), nullable=False),
        sa.Column("rubric_json", sa.JSON(), nullable=False),
        sa.Column("focus_notes", sa.Text(), nullable=False),
        sa.Column("template_key", sa.String(length=255), nullable=False),
        sa.Column("tech_stack", sa.String(length=255), nullable=False),
        sa.Column("seniority", sa.String(length=100), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("model_version", sa.String(length=255), nullable=True),
        sa.Column("prompt_version", sa.String(length=255), nullable=True),
        sa.Column("rubric_version", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft','ready','locked')", name="ck_scenario_versions_status"
        ),
        sa.ForeignKeyConstraint(["trial_id"], [f"{parent_table_name}.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trial_id",
            "version_index",
            name="uq_scenario_versions_trial_version_index",
        ),
    )
    op.create_index(
        "ix_scenario_versions_trial_id",
        "scenario_versions",
        ["trial_id"],
        unique=False,
    )
    op.add_column(
        parent_table_name,
        sa.Column("active_scenario_version_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_trials_active_scenario_version_id",
        parent_table_name,
        "scenario_versions",
        ["active_scenario_version_id"],
        ["id"],
    )
    op.add_column(
        "candidate_sessions",
        sa.Column("scenario_version_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_candidate_sessions_scenario_version_id",
        "candidate_sessions",
        "scenario_versions",
        ["scenario_version_id"],
        ["id"],
    )
    op.create_index(
        "ix_candidate_sessions_scenario_version_id",
        "candidate_sessions",
        ["scenario_version_id"],
        unique=False,
    )


def finalize_upgrade(op: object) -> None:
    """Execute finalize upgrade."""
    parent_table_name = _parent_table_name(op)
    op.alter_column(
        "candidate_sessions",
        "scenario_version_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_check_constraint(
        TRIAL_ACTIVE_SCENARIO_REQUIRED_CHECK_NAME,
        parent_table_name,
        TRIAL_ACTIVE_SCENARIO_REQUIRED_CHECK_EXPR,
    )


def run_downgrade_schema(op: object) -> None:
    """Run downgrade schema."""
    parent_table_name = _parent_table_name(op)
    op.drop_constraint(
        TRIAL_ACTIVE_SCENARIO_REQUIRED_CHECK_NAME,
        parent_table_name,
        type_="check",
    )
    op.alter_column(
        "candidate_sessions",
        "scenario_version_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.drop_index(
        "ix_candidate_sessions_scenario_version_id", table_name="candidate_sessions"
    )
    op.drop_constraint(
        "fk_candidate_sessions_scenario_version_id",
        "candidate_sessions",
        type_="foreignkey",
    )
    op.drop_column("candidate_sessions", "scenario_version_id")
    op.drop_constraint(
        "fk_trials_active_scenario_version_id",
        parent_table_name,
        type_="foreignkey",
    )
    op.drop_column(parent_table_name, "active_scenario_version_id")
    op.drop_index("ix_scenario_versions_trial_id", table_name="scenario_versions")
    op.drop_table("scenario_versions")
