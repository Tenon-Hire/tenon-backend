"""Backfill scenario versions and link existing sessions."""

from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa

from .constants import DEFAULT_TEMPLATE_KEY
from .introspection import has_column, table_exists


def ensure_scenario_versions_backfill(bind: sa.Connection) -> None:
    """Ensure scenario versions backfill."""
    if not table_exists(bind, "scenario_versions"):
        return
    if not has_column(bind, "simulations", "active_scenario_version_id"):
        return
    if not has_column(bind, "candidate_sessions", "scenario_version_id"):
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
            "SELECT id, status, title, role, tech_stack, seniority, focus, "
            "scenario_template, template_key, created_at, activated_at, terminated_at "
            "FROM simulations"
        )
    ).mappings()
    for row in simulation_rows:
        simulation_id = int(row["id"])
        existing_id = bind.execute(
            sa.text(
                "SELECT id FROM scenario_versions "
                "WHERE simulation_id = :simulation_id AND version_index = 1"
            ),
            {"simulation_id": simulation_id},
        ).scalar_one_or_none()
        scenario_id = (
            int(existing_id)
            if existing_id is not None
            else _create_v1(bind, scenario_versions, row)
        )
        bind.execute(
            sa.text(
                "UPDATE simulations SET active_scenario_version_id = "
                "COALESCE(active_scenario_version_id, :scenario_id) WHERE id = :simulation_id"
            ),
            {"scenario_id": scenario_id, "simulation_id": simulation_id},
        )

    bind.execute(
        sa.text(
            "UPDATE candidate_sessions cs SET scenario_version_id = s.active_scenario_version_id "
            "FROM simulations s WHERE cs.simulation_id = s.id "
            "AND cs.scenario_version_id IS NULL AND s.active_scenario_version_id IS NOT NULL"
        )
    )


def _create_v1(
    bind: sa.Connection,
    scenario_versions: sa.Table,
    row: sa.RowMapping,
) -> int:
    raw_status = str(row.get("status") or "").strip()
    locked_at = None
    if raw_status in {"active_inviting", "terminated"}:
        locked_at = (
            row.get("activated_at") or row.get("terminated_at") or datetime.now(UTC)
        )
    storyline_md = (
        f"# {str(row.get('title') or '').strip()}\n\n"
        f"Role: {str(row.get('role') or '').strip()}\n"
        f"Template: {str(row.get('scenario_template') or '').strip()}"
    ).strip()
    return int(
        bind.execute(
            sa.insert(scenario_versions)
            .values(
                simulation_id=int(row["id"]),
                version_index=1,
                status="locked" if locked_at else "ready",
                storyline_md=storyline_md,
                task_prompts_json=[],
                rubric_json={},
                focus_notes=str(row.get("focus") or ""),
                template_key=str(row.get("template_key") or DEFAULT_TEMPLATE_KEY),
                tech_stack=str(row.get("tech_stack") or ""),
                seniority=str(row.get("seniority") or ""),
                created_at=row.get("created_at") or datetime.now(UTC),
                locked_at=locked_at,
            )
            .returning(scenario_versions.c.id)
        ).scalar_one()
    )
