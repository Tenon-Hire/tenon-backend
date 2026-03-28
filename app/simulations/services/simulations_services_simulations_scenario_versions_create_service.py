"""Application module for simulations services simulations scenario versions create service workflows."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    ScenarioVersion,
    Simulation,
    Task,
)
from app.simulations.repositories.scenario_versions import (
    simulations_repositories_scenario_versions_simulations_scenario_versions_repository as scenario_repo,
)
from app.simulations.repositories.scenario_versions.simulations_repositories_scenario_versions_simulations_scenario_versions_model import (
    SCENARIO_VERSION_STATUS_READY,
)
from app.simulations.services.simulations_services_simulations_scenario_versions_defaults_service import (
    default_storyline_md,
    task_prompts_payload,
)

logger = logging.getLogger(__name__)


async def create_initial_scenario_version(
    db: AsyncSession,
    *,
    simulation: Simulation,
    tasks: list[Task],
) -> ScenarioVersion:
    """Create initial scenario version."""
    scenario_version = ScenarioVersion(
        simulation_id=simulation.id,
        version_index=1,
        status=SCENARIO_VERSION_STATUS_READY,
        storyline_md=default_storyline_md(simulation),
        task_prompts_json=task_prompts_payload(tasks),
        rubric_json={},
        focus_notes=simulation.focus or "",
        template_key=simulation.template_key,
        tech_stack=simulation.tech_stack,
        seniority=simulation.seniority,
    )
    db.add(scenario_version)
    await db.flush()
    simulation.active_scenario_version_id = scenario_version.id
    await db.flush()
    logger.info(
        "Scenario version created simulationId=%s scenarioVersionId=%s versionIndex=%s",
        simulation.id,
        scenario_version.id,
        scenario_version.version_index,
    )
    return scenario_version


async def get_active_scenario_version(
    db: AsyncSession, simulation_id: int
) -> ScenarioVersion | None:
    """Return active scenario version."""
    return await scenario_repo.get_active_for_simulation(db, simulation_id)
