"""Reconcile schema drift for locally stamped databases.

Revision ID: 202603190001
Revises: 202603150002
Create Date: 2026-03-19 00:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "202603190001"
down_revision: str | Sequence[str] | None = "202603150002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEFAULT_TEMPLATE_KEY = "python-fastapi"
_RECORDING_STATUS_CHECK_NAME = "ck_recording_assets_status"
_RECORDING_STATUS_CHECK_EXPR = (
    "status IN ("
    "'uploading','uploaded','processing','ready','failed','deleted','purged'"
    ")"
)


def _column_names(bind: sa.Connection, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def _has_column(bind: sa.Connection, table_name: str, column_name: str) -> bool:
    return column_name in _column_names(bind, table_name)


def _fk_names(bind: sa.Connection, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {
        fk["name"] for fk in inspector.get_foreign_keys(table_name) if fk.get("name")
    }


def _index_names(bind: sa.Connection, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {idx["name"] for idx in inspector.get_indexes(table_name) if idx.get("name")}


def _check_names(bind: sa.Connection, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    checks = inspector.get_check_constraints(table_name) or []
    return {check["name"] for check in checks if check.get("name")}


def _add_column_if_missing(
    bind: sa.Connection,
    table_name: str,
    column: sa.Column[object],
) -> None:
    if not _has_column(bind, table_name, column.name):
        op.add_column(table_name, column)


def _add_fk_if_missing(
    bind: sa.Connection,
    *,
    name: str,
    source_table: str,
    referent_table: str,
    local_cols: list[str],
    remote_cols: list[str],
) -> None:
    if name not in _fk_names(bind, source_table):
        op.create_foreign_key(
            name,
            source_table,
            referent_table,
            local_cols,
            remote_cols,
        )


def _add_index_if_missing(
    bind: sa.Connection,
    *,
    name: str,
    table_name: str,
    columns: list[str],
    unique: bool = False,
) -> None:
    if name not in _index_names(bind, table_name):
        op.create_index(name, table_name, columns, unique=unique)


def _table_exists(bind: sa.Connection, table_name: str) -> bool:
    return table_name in set(sa.inspect(bind).get_table_names())


def _ensure_scenario_versions_backfill(bind: sa.Connection) -> None:
    if not _table_exists(bind, "scenario_versions"):
        return
    if not _has_column(bind, "simulations", "active_scenario_version_id"):
        return
    if not _has_column(bind, "candidate_sessions", "scenario_version_id"):
        return

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

    simulation_rows = bind.execute(
        sa.text(
            """
            SELECT
              id,
              status,
              title,
              role,
              tech_stack,
              seniority,
              focus,
              scenario_template,
              template_key,
              created_at,
              activated_at,
              terminated_at
            FROM simulations
            """
        )
    ).mappings()

    for row in simulation_rows:
        simulation_id = int(row["id"])
        existing_scenario_id = bind.execute(
            sa.text(
                """
                SELECT id
                FROM scenario_versions
                WHERE simulation_id = :simulation_id
                  AND version_index = 1
                """
            ),
            {"simulation_id": simulation_id},
        ).scalar_one_or_none()

        scenario_id: int
        if existing_scenario_id is None:
            raw_status = str(row.get("status") or "").strip()
            is_locked = raw_status in {"active_inviting", "terminated"}
            locked_at = None
            if is_locked:
                locked_at = (
                    row.get("activated_at")
                    or row.get("terminated_at")
                    or datetime.now(UTC)
                )
            storyline_md = (
                f"# {str(row.get('title') or '').strip()}\n\n"
                f"Role: {str(row.get('role') or '').strip()}\n"
                f"Template: {str(row.get('scenario_template') or '').strip()}"
            ).strip()
            scenario_id = int(
                bind.execute(
                    sa.insert(scenario_versions)
                    .values(
                        simulation_id=simulation_id,
                        version_index=1,
                        status="locked" if is_locked else "ready",
                        storyline_md=storyline_md,
                        task_prompts_json=[],
                        rubric_json={},
                        focus_notes=str(row.get("focus") or ""),
                        template_key=str(
                            row.get("template_key") or _DEFAULT_TEMPLATE_KEY
                        ),
                        tech_stack=str(row.get("tech_stack") or ""),
                        seniority=str(row.get("seniority") or ""),
                        created_at=row.get("created_at") or datetime.now(UTC),
                        locked_at=locked_at,
                    )
                    .returning(scenario_versions.c.id)
                ).scalar_one()
            )
        else:
            scenario_id = int(existing_scenario_id)

        bind.execute(
            sa.text(
                """
                UPDATE simulations
                   SET active_scenario_version_id = COALESCE(
                     active_scenario_version_id, :scenario_id
                   )
                 WHERE id = :simulation_id
                """
            ),
            {
                "scenario_id": scenario_id,
                "simulation_id": simulation_id,
            },
        )

    bind.execute(
        sa.text(
            """
            UPDATE candidate_sessions cs
               SET scenario_version_id = s.active_scenario_version_id
              FROM simulations s
             WHERE cs.simulation_id = s.id
               AND cs.scenario_version_id IS NULL
               AND s.active_scenario_version_id IS NOT NULL
            """
        )
    )


def _reconcile_recording_status_check(bind: sa.Connection) -> None:
    if bind.dialect.name != "postgresql":
        return
    check_names = _check_names(bind, "recording_assets")
    if _RECORDING_STATUS_CHECK_NAME in check_names:
        op.drop_constraint(
            _RECORDING_STATUS_CHECK_NAME,
            "recording_assets",
            type_="check",
        )
    op.create_check_constraint(
        _RECORDING_STATUS_CHECK_NAME,
        "recording_assets",
        _RECORDING_STATUS_CHECK_EXPR,
    )


def upgrade() -> None:
    bind = op.get_bind()

    # simulations
    _add_column_if_missing(
        bind,
        "simulations",
        sa.Column("active_scenario_version_id", sa.Integer(), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "simulations",
        sa.Column("pending_scenario_version_id", sa.Integer(), nullable=True),
    )

    # candidate_sessions
    _add_column_if_missing(
        bind,
        "candidate_sessions",
        sa.Column("scenario_version_id", sa.Integer(), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "candidate_sessions",
        sa.Column("consent_version", sa.String(length=100), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "candidate_sessions",
        sa.Column("consent_timestamp", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "candidate_sessions",
        sa.Column("ai_notice_version", sa.String(length=100), nullable=True),
    )

    # recording_assets
    _add_column_if_missing(
        bind,
        "recording_assets",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "recording_assets",
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "recording_assets",
        sa.Column("consent_version", sa.String(length=100), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "recording_assets",
        sa.Column("consent_timestamp", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "recording_assets",
        sa.Column("ai_notice_version", sa.String(length=100), nullable=True),
    )

    # submissions
    _add_column_if_missing(
        bind,
        "submissions",
        sa.Column("recording_id", sa.Integer(), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "submissions",
        sa.Column("checkpoint_sha", sa.String(length=100), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "submissions",
        sa.Column("final_sha", sa.String(length=100), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "submissions",
        sa.Column("workflow_run_attempt", sa.Integer(), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "submissions",
        sa.Column("workflow_run_status", sa.String(length=50), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "submissions",
        sa.Column("workflow_run_conclusion", sa.String(length=50), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "submissions",
        sa.Column("workflow_run_completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # transcripts
    _add_column_if_missing(
        bind,
        "transcripts",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # workspace_groups
    _add_column_if_missing(
        bind,
        "workspace_groups",
        sa.Column("cleanup_status", sa.String(length=20), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "workspace_groups",
        sa.Column("cleanup_attempted_at", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "workspace_groups",
        sa.Column("cleaned_at", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "workspace_groups",
        sa.Column("cleanup_error", sa.Text(), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "workspace_groups",
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "workspace_groups",
        sa.Column("access_revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "workspace_groups",
        sa.Column("access_revocation_error", sa.Text(), nullable=True),
    )

    # workspaces
    _add_column_if_missing(
        bind,
        "workspaces",
        sa.Column("workspace_group_id", sa.String(length=36), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "workspaces",
        sa.Column("precommit_sha", sa.String(length=100), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "workspaces",
        sa.Column("precommit_details_json", sa.Text(), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "workspaces",
        sa.Column("cleanup_status", sa.String(length=20), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "workspaces",
        sa.Column("cleanup_attempted_at", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "workspaces",
        sa.Column("cleaned_at", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "workspaces",
        sa.Column("cleanup_error", sa.Text(), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "workspaces",
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "workspaces",
        sa.Column("access_revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing(
        bind,
        "workspaces",
        sa.Column("access_revocation_error", sa.Text(), nullable=True),
    )

    _ensure_scenario_versions_backfill(bind)

    # Foreign keys and indexes that are safe to add after reconciliation.
    _add_fk_if_missing(
        bind,
        name="fk_simulations_active_scenario_version_id",
        source_table="simulations",
        referent_table="scenario_versions",
        local_cols=["active_scenario_version_id"],
        remote_cols=["id"],
    )
    _add_fk_if_missing(
        bind,
        name="fk_simulations_pending_scenario_version_id",
        source_table="simulations",
        referent_table="scenario_versions",
        local_cols=["pending_scenario_version_id"],
        remote_cols=["id"],
    )
    _add_fk_if_missing(
        bind,
        name="fk_candidate_sessions_scenario_version_id",
        source_table="candidate_sessions",
        referent_table="scenario_versions",
        local_cols=["scenario_version_id"],
        remote_cols=["id"],
    )
    _add_fk_if_missing(
        bind,
        name="submissions_recording_id_fkey",
        source_table="submissions",
        referent_table="recording_assets",
        local_cols=["recording_id"],
        remote_cols=["id"],
    )
    _add_fk_if_missing(
        bind,
        name="workspaces_workspace_group_id_fkey",
        source_table="workspaces",
        referent_table="workspace_groups",
        local_cols=["workspace_group_id"],
        remote_cols=["id"],
    )

    _add_index_if_missing(
        bind,
        name="ix_candidate_sessions_scenario_version_id",
        table_name="candidate_sessions",
        columns=["scenario_version_id"],
        unique=False,
    )
    _add_index_if_missing(
        bind,
        name="ix_submissions_recording_id",
        table_name="submissions",
        columns=["recording_id"],
        unique=False,
    )
    unique_constraint_names = {
        item["name"]
        for item in sa.inspect(bind).get_unique_constraints("workspaces")
        if item.get("name")
    }
    workspace_index_names = _index_names(bind, "workspaces")
    if (
        "uq_workspaces_workspace_group_id" not in unique_constraint_names
        and "uq_workspaces_workspace_group_id" not in workspace_index_names
    ):
        op.create_unique_constraint(
            "uq_workspaces_workspace_group_id",
            "workspaces",
            ["workspace_group_id"],
        )

    _reconcile_recording_status_check(bind)


def downgrade() -> None:
    # This reconciliation migration is intentionally non-reversible.
    pass
