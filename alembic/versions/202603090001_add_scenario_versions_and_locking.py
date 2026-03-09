"""Add scenario_versions persistence and simulation active scenario pointer.

Revision ID: 202603090001
Revises: 202603080004
Create Date: 2026-03-09 00:01:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "202603090001"
down_revision: str | Sequence[str] | None = "202603080004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEFAULT_TEMPLATE_KEY = "python-fastapi"
_SIMULATION_ACTIVE_SCENARIO_REQUIRED_CHECK_NAME = (
    "ck_simulations_active_scenario_required"
)
_SIMULATION_ACTIVE_SCENARIO_REQUIRED_CHECK_EXPR = (
    "status IN ('draft','generating') OR active_scenario_version_id IS NOT NULL"
)


def _row_get(row: Any, key: str) -> Any:
    if hasattr(row, "_mapping"):
        return row._mapping.get(key)
    if isinstance(row, dict):
        return row.get(key)
    return getattr(row, key, None)


def upgrade() -> None:
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
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft','ready','locked')",
            name="ck_scenario_versions_status",
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

    conn = op.get_bind()

    simulations = sa.table(
        "simulations",
        sa.column("id", sa.Integer()),
        sa.column("active_scenario_version_id", sa.Integer()),
        sa.column("status", sa.String()),
        sa.column("title", sa.String()),
        sa.column("role", sa.String()),
        sa.column("tech_stack", sa.String()),
        sa.column("seniority", sa.String()),
        sa.column("focus", sa.Text()),
        sa.column("scenario_template", sa.String()),
        sa.column("template_key", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("activated_at", sa.DateTime(timezone=True)),
        sa.column("terminated_at", sa.DateTime(timezone=True)),
    )
    scenario_versions = sa.table(
        "scenario_versions",
        sa.column("id", sa.Integer()),
        sa.column("simulation_id", sa.Integer()),
        sa.column("version_index", sa.Integer()),
        sa.column("status", sa.String()),
        sa.column("storyline_md", sa.Text()),
        sa.column("task_prompts_json", sa.JSON()),
        sa.column("rubric_json", sa.JSON()),
        sa.column("focus_notes", sa.Text()),
        sa.column("template_key", sa.String()),
        sa.column("tech_stack", sa.String()),
        sa.column("seniority", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("locked_at", sa.DateTime(timezone=True)),
    )
    candidate_sessions = sa.table(
        "candidate_sessions",
        sa.column("simulation_id", sa.Integer()),
        sa.column("scenario_version_id", sa.Integer()),
    )

    simulation_rows = conn.execute(
        sa.select(
            simulations.c.id,
            simulations.c.status,
            simulations.c.title,
            simulations.c.role,
            simulations.c.tech_stack,
            simulations.c.seniority,
            simulations.c.focus,
            simulations.c.scenario_template,
            simulations.c.template_key,
            simulations.c.created_at,
            simulations.c.activated_at,
            simulations.c.terminated_at,
        )
    ).all()

    for row in simulation_rows:
        simulation_id = int(_row_get(row, "id"))
        raw_status = str(_row_get(row, "status") or "")
        is_locked = raw_status in {"active_inviting", "terminated"}
        locked_at = (
            _row_get(row, "activated_at")
            or _row_get(row, "terminated_at")
            or datetime.now(UTC)
            if is_locked
            else None
        )
        title = str(_row_get(row, "title") or "").strip()
        role = str(_row_get(row, "role") or "").strip()
        scenario_template = str(_row_get(row, "scenario_template") or "").strip()
        storyline_md = (
            f"# {title}\n\nRole: {role}\nTemplate: {scenario_template}".strip()
        )

        conn.execute(
            sa.insert(scenario_versions).values(
                simulation_id=simulation_id,
                version_index=1,
                status="locked" if is_locked else "ready",
                storyline_md=storyline_md,
                task_prompts_json=[],
                rubric_json={},
                focus_notes=str(_row_get(row, "focus") or ""),
                template_key=str(_row_get(row, "template_key") or _DEFAULT_TEMPLATE_KEY),
                tech_stack=str(_row_get(row, "tech_stack") or ""),
                seniority=str(_row_get(row, "seniority") or ""),
                created_at=_row_get(row, "created_at") or datetime.now(UTC),
                locked_at=locked_at,
            )
        )

        scenario_id = conn.execute(
            sa.select(scenario_versions.c.id).where(
                scenario_versions.c.simulation_id == simulation_id,
                scenario_versions.c.version_index == 1,
            )
        ).scalar_one()

        conn.execute(
            sa.update(simulations)
            .where(simulations.c.id == simulation_id)
            .values(active_scenario_version_id=scenario_id)
        )
        conn.execute(
            sa.update(candidate_sessions)
            .where(candidate_sessions.c.simulation_id == simulation_id)
            .values(scenario_version_id=scenario_id)
        )

    op.alter_column(
        "candidate_sessions",
        "scenario_version_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_check_constraint(
        _SIMULATION_ACTIVE_SCENARIO_REQUIRED_CHECK_NAME,
        "simulations",
        _SIMULATION_ACTIVE_SCENARIO_REQUIRED_CHECK_EXPR,
    )


def downgrade() -> None:
    op.drop_constraint(
        _SIMULATION_ACTIVE_SCENARIO_REQUIRED_CHECK_NAME,
        "simulations",
        type_="check",
    )
    op.alter_column(
        "candidate_sessions",
        "scenario_version_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.drop_index(
        "ix_candidate_sessions_scenario_version_id",
        table_name="candidate_sessions",
    )
    op.drop_constraint(
        "fk_candidate_sessions_scenario_version_id",
        "candidate_sessions",
        type_="foreignkey",
    )
    op.drop_column("candidate_sessions", "scenario_version_id")

    op.drop_constraint(
        "fk_simulations_active_scenario_version_id",
        "simulations",
        type_="foreignkey",
    )
    op.drop_column("simulations", "active_scenario_version_id")

    op.drop_index("ix_scenario_versions_simulation_id", table_name="scenario_versions")
    op.drop_table("scenario_versions")
