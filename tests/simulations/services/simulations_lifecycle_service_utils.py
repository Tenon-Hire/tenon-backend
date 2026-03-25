from __future__ import annotations

# helper import baseline for restructure-compat
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select

from app.shared.database.shared_database_models_model import (
    Company,
    Job,
    ScenarioVersion,
    Simulation,
    User,
)
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.simulations import services as sim_service
from app.simulations.services import (
    simulations_services_simulations_lifecycle_service as lifecycle_service,
)


def _simulation(status: str) -> Simulation:
    return Simulation(
        company_id=1,
        title="Lifecycle",
        role="Backend Engineer",
        tech_stack="Python",
        seniority="Mid",
        focus="Test",
        scenario_template="default-5day-node-postgres",
        created_by=1,
        status=status,
    )


async def _attach_active_scenario(async_session, simulation: Simulation) -> None:
    scenario = ScenarioVersion(
        simulation_id=simulation.id,
        version_index=1,
        status="ready",
        storyline_md=f"# {simulation.title}",
        task_prompts_json=[],
        rubric_json={},
        focus_notes=simulation.focus or "",
        template_key=simulation.template_key,
        tech_stack=simulation.tech_stack,
        seniority=simulation.seniority,
    )
    async_session.add(scenario)
    await async_session.flush()
    simulation.active_scenario_version_id = scenario.id
    await async_session.flush()


__all__ = [name for name in globals() if not name.startswith("__")]
