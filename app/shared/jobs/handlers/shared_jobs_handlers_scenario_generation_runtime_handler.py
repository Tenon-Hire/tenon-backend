"""Application module for jobs handlers scenario generation runtime handler workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter

from sqlalchemy import select

from app.shared.database.shared_database_models_model import Simulation, Task
from app.simulations.repositories.simulations_repositories_simulations_simulation_model import (
    SIMULATION_STATUS_ACTIVE_INVITING,
    SIMULATION_STATUS_GENERATING,
    SIMULATION_STATUS_READY_FOR_REVIEW,
    SIMULATION_STATUS_TERMINATED,
)


async def handle_scenario_generation_impl(
    payload_json: dict,
    *,
    parse_positive_int,
    async_session_maker,
    normalize_simulation_status,
    generate_scenario_payload,
    apply_generated_task_updates,
    apply_status_transition,
    apply_requested_scenario_version,
    apply_default_scenario_version,
    logger,
):
    """Handle scenario generation impl."""
    started = perf_counter()
    simulation_id = parse_positive_int(payload_json.get("simulationId"))
    if simulation_id is None:
        return {"status": "skipped_invalid_payload", "simulationId": None}
    requested_scenario_version_id = parse_positive_int(
        payload_json.get("scenarioVersionId")
    )
    source = model_name = model_version = prompt_version = rubric_version = None
    scenario_version_id = None
    created_new = False
    async with async_session_maker() as db:
        simulation = (
            await db.execute(
                select(Simulation)
                .where(Simulation.id == simulation_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if simulation is None:
            return {"status": "simulation_not_found", "simulationId": simulation_id}
        current_status = normalize_simulation_status(simulation.status)
        if current_status == SIMULATION_STATUS_TERMINATED:
            return {
                "status": "skipped_non_mutable_simulation",
                "simulationId": simulation_id,
                "simulationStatus": current_status,
            }
        if current_status not in {
            SIMULATION_STATUS_GENERATING,
            SIMULATION_STATUS_READY_FOR_REVIEW,
            SIMULATION_STATUS_ACTIVE_INVITING,
        }:
            return {
                "status": "skipped_unexpected_status",
                "simulationId": simulation_id,
                "simulationStatus": current_status,
            }
        tasks = (
            (
                await db.execute(
                    select(Task)
                    .where(Task.simulation_id == simulation.id)
                    .order_by(Task.day_index.asc())
                )
            )
            .scalars()
            .all()
        )
        if not tasks:
            raise RuntimeError("scenario_generation_missing_seeded_tasks")
        generated = generate_scenario_payload(
            role=simulation.role,
            tech_stack=simulation.tech_stack,
            template_key=simulation.template_key,
        )
        if requested_scenario_version_id is not None:
            early, scenario_version_id = await apply_requested_scenario_version(
                db,
                simulation=simulation,
                requested_scenario_version_id=requested_scenario_version_id,
                generated=generated,
            )
            if early is not None:
                return early
        else:
            (
                early,
                scenario_version_id,
                created_new,
            ) = await apply_default_scenario_version(
                db,
                simulation=simulation,
                current_status=current_status,
                generated=generated,
            )
            if early is not None:
                return early
        apply_generated_task_updates(
            tasks=tasks,
            task_prompts_json=generated.task_prompts_json,
            rubric_json=generated.rubric_json,
        )
        apply_status_transition(
            simulation,
            target_status=SIMULATION_STATUS_READY_FOR_REVIEW,
            changed_at=datetime.now(UTC),
        )
        await db.commit()
        source = generated.metadata.source
        model_name = generated.metadata.model_name
        model_version = generated.metadata.model_version
        prompt_version = generated.metadata.prompt_version
        rubric_version = generated.metadata.rubric_version
    elapsed_ms = int((perf_counter() - started) * 1000)
    logger.info(
        "scenario_generation_job_completed",
        extra={
            "simulationId": simulation_id,
            "scenarioVersionId": scenario_version_id,
            "createdScenarioVersion": created_new,
            "source": source,
            "modelName": model_name,
            "modelVersion": model_version,
            "promptVersion": prompt_version,
            "rubricVersion": rubric_version,
            "latencyMs": elapsed_ms,
        },
    )
    return {
        "status": "completed",
        "simulationId": simulation_id,
        "scenarioVersionId": scenario_version_id,
        "source": source,
        "modelName": model_name,
        "modelVersion": model_version,
        "promptVersion": prompt_version,
        "rubricVersion": rubric_version,
        "latencyMs": elapsed_ms,
    }


__all__ = ["handle_scenario_generation_impl"]
