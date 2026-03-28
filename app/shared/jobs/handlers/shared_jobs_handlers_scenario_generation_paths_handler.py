"""Application module for jobs handlers scenario generation paths handler workflows."""

from __future__ import annotations

from sqlalchemy import select

from app.shared.database.shared_database_models_model import ScenarioVersion
from app.simulations.repositories.scenario_versions.simulations_repositories_scenario_versions_simulations_scenario_versions_model import (
    SCENARIO_VERSION_STATUS_LOCKED,
    SCENARIO_VERSION_STATUS_READY,
)
from app.simulations.repositories.simulations_repositories_simulations_simulation_model import (
    SIMULATION_STATUS_GENERATING,
)


def _apply_generated_fields(target_scenario, *, simulation, generated):
    target_scenario.status = SCENARIO_VERSION_STATUS_READY
    target_scenario.storyline_md = generated.storyline_md
    target_scenario.task_prompts_json = generated.task_prompts_json
    target_scenario.rubric_json = generated.rubric_json
    target_scenario.focus_notes = simulation.focus or ""
    target_scenario.template_key = simulation.template_key
    target_scenario.tech_stack = simulation.tech_stack
    target_scenario.seniority = simulation.seniority
    target_scenario.model_name = generated.metadata.model_name
    target_scenario.model_version = generated.metadata.model_version
    target_scenario.prompt_version = generated.metadata.prompt_version
    target_scenario.rubric_version = generated.metadata.rubric_version
    target_scenario.locked_at = None


async def _apply_requested_scenario_version(
    db, *, simulation, requested_scenario_version_id: int, generated
):
    target_scenario = (
        await db.execute(
            select(ScenarioVersion)
            .where(
                ScenarioVersion.id == requested_scenario_version_id,
                ScenarioVersion.simulation_id == simulation.id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if target_scenario is None:
        return {
            "status": "scenario_version_not_found",
            "simulationId": simulation.id,
            "scenarioVersionId": requested_scenario_version_id,
        }, None
    if target_scenario.status == SCENARIO_VERSION_STATUS_LOCKED:
        return {
            "status": "skipped_locked_scenario_version",
            "simulationId": simulation.id,
            "scenarioVersionId": target_scenario.id,
        }, None
    _apply_generated_fields(target_scenario, simulation=simulation, generated=generated)
    return None, target_scenario.id


async def _apply_default_scenario_version(
    db, *, simulation, current_status: str | None, generated
):
    existing_v1 = (
        await db.execute(
            select(ScenarioVersion)
            .where(
                ScenarioVersion.simulation_id == simulation.id,
                ScenarioVersion.version_index == 1,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if (
        current_status != SIMULATION_STATUS_GENERATING
        and simulation.active_scenario_version_id is not None
        and (
            existing_v1 is None
            or simulation.active_scenario_version_id != existing_v1.id
        )
    ):
        return (
            {
                "status": "skipped_active_version_moved",
                "simulationId": simulation.id,
                "activeScenarioVersionId": simulation.active_scenario_version_id,
            },
            None,
            False,
        )
    scenario_v1 = existing_v1
    created_new = scenario_v1 is None
    if scenario_v1 is None:
        scenario_v1 = ScenarioVersion(
            simulation_id=simulation.id,
            version_index=1,
            status=SCENARIO_VERSION_STATUS_READY,
            storyline_md="",
            task_prompts_json=[],
            rubric_json={},
            focus_notes=simulation.focus or "",
            template_key=simulation.template_key,
            tech_stack=simulation.tech_stack,
            seniority=simulation.seniority,
        )
        db.add(scenario_v1)
        await db.flush()
    _apply_generated_fields(scenario_v1, simulation=simulation, generated=generated)
    simulation.active_scenario_version_id = scenario_v1.id
    return None, scenario_v1.id, created_new


__all__ = ["_apply_default_scenario_version", "_apply_requested_scenario_version"]
