"""Data backfill for scenario_versions migration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa

from app.core.db.migrations.shared_trial_schema_compat import (
    resolve_candidate_session_parent_column_name,
)

from .constants import DEFAULT_TEMPLATE_KEY
from .table_refs import table_refs


def _row_get(row: Any, key: str) -> Any:
    if hasattr(row, "_mapping"):
        return row._mapping.get(key)
    if isinstance(row, dict):
        return row.get(key)
    return getattr(row, key, None)


def run_backfill(conn: sa.Connection) -> None:
    """Run backfill."""
    trials, scenario_versions, candidate_sessions = table_refs(conn)
    candidate_session_parent_column = resolve_candidate_session_parent_column_name(conn)
    trial_rows = conn.execute(
        sa.select(
            trials.c.id,
            trials.c.status,
            trials.c.title,
            trials.c.role,
            trials.c.tech_stack,
            trials.c.seniority,
            trials.c.focus,
            trials.c.scenario_template,
            trials.c.template_key,
            trials.c.created_at,
            trials.c.activated_at,
            trials.c.terminated_at,
        )
    ).all()
    for row in trial_rows:
        trial_id = int(_row_get(row, "id"))
        raw_status = str(_row_get(row, "status") or "")
        locked_at = None
        if raw_status in {"active_inviting", "terminated"}:
            locked_at = (
                _row_get(row, "activated_at")
                or _row_get(row, "terminated_at")
                or datetime.now(UTC)
            )
        storyline_md = (
            f"# {str(_row_get(row, 'title') or '').strip()}\n\n"
            f"Role: {str(_row_get(row, 'role') or '').strip()}\n"
            f"Template: {str(_row_get(row, 'scenario_template') or '').strip()}"
        ).strip()
        conn.execute(
            sa.insert(scenario_versions).values(
                trial_id=trial_id,
                version_index=1,
                status="locked" if locked_at else "ready",
                storyline_md=storyline_md,
                task_prompts_json=[],
                rubric_json={},
                focus_notes=str(_row_get(row, "focus") or ""),
                template_key=str(_row_get(row, "template_key") or DEFAULT_TEMPLATE_KEY),
                tech_stack=str(_row_get(row, "tech_stack") or ""),
                seniority=str(_row_get(row, "seniority") or ""),
                created_at=_row_get(row, "created_at") or datetime.now(UTC),
                locked_at=locked_at,
            )
        )
        scenario_id = conn.execute(
            sa.select(scenario_versions.c.id).where(
                scenario_versions.c.trial_id == trial_id,
                scenario_versions.c.version_index == 1,
            )
        ).scalar_one()
        conn.execute(
            sa.update(trials)
            .where(trials.c.id == trial_id)
            .values(active_scenario_version_id=scenario_id)
        )
        conn.execute(
            sa.update(candidate_sessions)
            .where(candidate_sessions.c[candidate_session_parent_column] == trial_id)
            .values(scenario_version_id=scenario_id)
        )
