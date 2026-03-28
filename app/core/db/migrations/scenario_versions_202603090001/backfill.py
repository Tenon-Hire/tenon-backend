"""Data backfill for scenario_versions migration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa

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
    simulations, scenario_versions, candidate_sessions = table_refs()
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
                simulation_id=simulation_id,
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
