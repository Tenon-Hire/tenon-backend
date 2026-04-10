"""SQLAlchemy table references for scenario version backfill."""

from __future__ import annotations

import sqlalchemy as sa

from app.core.db.migrations.shared_trial_schema_compat import (
    resolve_candidate_session_parent_column_name,
    resolve_trial_parent_table_name,
)


def table_refs(
    bind: sa.Connection | None = None,
) -> tuple[sa.Table, sa.Table, sa.Table]:
    """Execute table refs."""
    parent_table_name = "trials"
    candidate_session_parent_column = "trial_id"
    if bind is not None:
        parent_table_name = resolve_trial_parent_table_name(bind)
        candidate_session_parent_column = resolve_candidate_session_parent_column_name(
            bind
        )

    trials = sa.table(
        parent_table_name,
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
        sa.column("trial_id", sa.Integer()),
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
        sa.column(candidate_session_parent_column, sa.Integer()),
        sa.column("scenario_version_id", sa.Integer()),
    )
    return trials, scenario_versions, candidate_sessions
