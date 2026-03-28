"""Application module for jobs handlers simulation cleanup handler workflows."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.shared.database import async_session_maker
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Simulation,
    Workspace,
)
from app.simulations.repositories.simulations_repositories_simulations_simulation_model import (
    SIMULATION_STATUS_TERMINATED,
)
from app.simulations.services.simulations_services_simulations_cleanup_jobs_service import (
    SIMULATION_CLEANUP_JOB_TYPE,
)


def _parse_simulation_id(payload_json: dict[str, Any]) -> int | None:
    raw_value = payload_json.get("simulationId")
    if isinstance(raw_value, bool):
        return None
    if isinstance(raw_value, int):
        return raw_value if raw_value > 0 else None
    if isinstance(raw_value, str) and raw_value.isdigit():
        parsed = int(raw_value)
        return parsed if parsed > 0 else None
    return None


async def handle_simulation_cleanup(payload_json: dict[str, Any]) -> dict[str, Any]:
    """Retry-safe no-op cleanup skeleton scoped to simulation-owned resources."""
    simulation_id = _parse_simulation_id(payload_json)
    if simulation_id is None:
        return {"status": "skipped_invalid_payload", "simulationId": None}

    async with async_session_maker() as db:
        simulation = (
            await db.execute(select(Simulation).where(Simulation.id == simulation_id))
        ).scalar_one_or_none()
        if simulation is None:
            return {"status": "simulation_not_found", "simulationId": simulation_id}
        if simulation.status != SIMULATION_STATUS_TERMINATED:
            return {
                "status": "skipped_not_terminated",
                "simulationId": simulation_id,
            }

        rows = (
            await db.execute(
                select(Workspace.repo_full_name, Workspace.template_repo_full_name)
                .join(
                    CandidateSession,
                    CandidateSession.id == Workspace.candidate_session_id,
                )
                .where(CandidateSession.simulation_id == simulation_id)
            )
        ).all()

    protected_template_repo_matches = sum(
        1 for repo_full_name, template_repo in rows if repo_full_name == template_repo
    )
    return {
        "status": "noop",
        "simulationId": simulation_id,
        "workspaceRepoCount": len(rows),
        "protectedTemplateRepoMatches": protected_template_repo_matches,
    }


__all__ = [
    "SIMULATION_CLEANUP_JOB_TYPE",
    "handle_simulation_cleanup",
]
