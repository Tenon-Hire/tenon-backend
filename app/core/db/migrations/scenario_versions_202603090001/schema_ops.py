"""Schema operations for scenario_versions migration."""

from __future__ import annotations

import sqlalchemy as sa

from .constants import (
    SIMULATION_ACTIVE_SCENARIO_REQUIRED_CHECK_EXPR,
    SIMULATION_ACTIVE_SCENARIO_REQUIRED_CHECK_NAME,
)


def create_schema(op: object) -> None:
    """Create schema."""
    op.create_table(
        "scenario_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("simulation_id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["simulation_id"], ["simulations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "simulation_id",
            "version_index",
            name="uq_scenario_versions_simulation_version_index",
        ),
    )
    op.create_index(
        "ix_scenario_versions_simulation_id",
        "scenario_versions",
        ["simulation_id"],
        unique=False,
    )
    op.add_column(
        "simulations",
        sa.Column("active_scenario_version_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_simulations_active_scenario_version_id",
        "simulations",
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
    op.alter_column(
        "candidate_sessions",
        "scenario_version_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_check_constraint(
        SIMULATION_ACTIVE_SCENARIO_REQUIRED_CHECK_NAME,
        "simulations",
        SIMULATION_ACTIVE_SCENARIO_REQUIRED_CHECK_EXPR,
    )


def run_downgrade_schema(op: object) -> None:
    """Run downgrade schema."""
    op.drop_constraint(
        SIMULATION_ACTIVE_SCENARIO_REQUIRED_CHECK_NAME, "simulations", type_="check"
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
        "fk_simulations_active_scenario_version_id", "simulations", type_="foreignkey"
    )
    op.drop_column("simulations", "active_scenario_version_id")
    op.drop_index("ix_scenario_versions_simulation_id", table_name="scenario_versions")
    op.drop_table("scenario_versions")
