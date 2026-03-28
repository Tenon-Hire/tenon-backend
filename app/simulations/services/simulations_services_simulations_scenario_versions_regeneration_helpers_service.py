"""Application module for simulations services simulations scenario versions regeneration helpers service workflows."""

from __future__ import annotations

import copy

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    Job,
    ScenarioVersion,
    Simulation,
)
from app.shared.jobs.repositories import repository as jobs_repo
from app.simulations.repositories.scenario_versions.simulations_repositories_scenario_versions_simulations_scenario_versions_model import (
    SCENARIO_VERSION_STATUS_GENERATING,
)
from app.simulations.services.simulations_services_simulations_scenario_generation_service import (
    SCENARIO_GENERATION_JOB_TYPE,
)
from app.simulations.services.simulations_services_simulations_scenario_payload_builder_service import (
    build_scenario_generation_payload,
)
from app.simulations.services.simulations_services_simulations_scenario_versions_access_service import (
    scenario_generation_idempotency_key,
)


def clone_pending_scenario(
    simulation: Simulation, active: ScenarioVersion, version_index: int
) -> ScenarioVersion:
    """Execute clone pending scenario."""
    return ScenarioVersion(
        simulation_id=simulation.id,
        version_index=version_index,
        status=SCENARIO_VERSION_STATUS_GENERATING,
        storyline_md=active.storyline_md,
        task_prompts_json=copy.deepcopy(active.task_prompts_json),
        rubric_json=copy.deepcopy(active.rubric_json),
        focus_notes=active.focus_notes,
        template_key=active.template_key,
        tech_stack=active.tech_stack,
        seniority=active.seniority,
        model_name=active.model_name,
        model_version=active.model_version,
        prompt_version=active.prompt_version,
        rubric_version=active.rubric_version,
        locked_at=None,
    )


async def enqueue_regeneration_job(
    db: AsyncSession, simulation: Simulation, regenerated: ScenarioVersion
) -> Job:
    """Enqueue regeneration job."""
    payload_json = build_scenario_generation_payload(simulation)
    payload_json["scenarioVersionId"] = regenerated.id
    return await jobs_repo.create_or_get_idempotent(
        db,
        job_type=SCENARIO_GENERATION_JOB_TYPE,
        idempotency_key=scenario_generation_idempotency_key(regenerated.id),
        payload_json=payload_json,
        company_id=simulation.company_id,
        correlation_id=f"simulation:{simulation.id}:scenario_version:{regenerated.id}",
        commit=False,
    )
