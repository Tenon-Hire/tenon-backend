from __future__ import annotations

import logging
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from sqlalchemy import select

from app.core.db import async_session_maker
from app.domains import ScenarioVersion, Simulation, Task
from app.repositories.scenario_versions.models import SCENARIO_VERSION_STATUS_READY
from app.repositories.simulations.simulation import (
    SIMULATION_STATUS_ACTIVE_INVITING,
    SIMULATION_STATUS_GENERATING,
    SIMULATION_STATUS_READY_FOR_REVIEW,
    SIMULATION_STATUS_TERMINATED,
)
from app.services.simulations.lifecycle import (
    apply_status_transition,
    normalize_simulation_status,
)
from app.services.simulations.scenario_generation import (
    SCENARIO_GENERATION_JOB_TYPE,
    apply_generated_task_updates,
    generate_scenario_payload,
)

logger = logging.getLogger(__name__)


def _parse_positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.isdigit():
        parsed = int(value)
        return parsed if parsed > 0 else None
    return None


async def handle_scenario_generation(payload_json: dict[str, Any]) -> dict[str, Any]:
    started = perf_counter()
    simulation_id = _parse_positive_int(payload_json.get("simulationId"))
    if simulation_id is None:
        return {"status": "skipped_invalid_payload", "simulationId": None}

    scenario_version_id: int | None = None
    source: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    prompt_version: str | None = None
    rubric_version: str | None = None
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
        if current_status in {
            SIMULATION_STATUS_ACTIVE_INVITING,
            SIMULATION_STATUS_TERMINATED,
        }:
            return {
                "status": "skipped_non_mutable_simulation",
                "simulationId": simulation_id,
                "simulationStatus": current_status,
            }

        if current_status not in {
            SIMULATION_STATUS_GENERATING,
            SIMULATION_STATUS_READY_FOR_REVIEW,
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

        # Second idempotency layer: retries/replays reuse ScenarioVersion v1
        # instead of inserting additional version-index 1 rows.
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
            return {
                "status": "skipped_active_version_moved",
                "simulationId": simulation_id,
                "activeScenarioVersionId": simulation.active_scenario_version_id,
            }

        generated = generate_scenario_payload(
            role=simulation.role,
            tech_stack=simulation.tech_stack,
            template_key=simulation.template_key,
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

        scenario_v1.status = SCENARIO_VERSION_STATUS_READY
        scenario_v1.storyline_md = generated.storyline_md
        scenario_v1.task_prompts_json = generated.task_prompts_json
        scenario_v1.rubric_json = generated.rubric_json
        scenario_v1.focus_notes = simulation.focus or ""
        scenario_v1.template_key = simulation.template_key
        scenario_v1.tech_stack = simulation.tech_stack
        scenario_v1.seniority = simulation.seniority
        scenario_v1.model_name = generated.metadata.model_name
        scenario_v1.model_version = generated.metadata.model_version
        scenario_v1.prompt_version = generated.metadata.prompt_version
        scenario_v1.rubric_version = generated.metadata.rubric_version

        apply_generated_task_updates(
            tasks=tasks,
            task_prompts_json=generated.task_prompts_json,
            rubric_json=generated.rubric_json,
        )

        simulation.active_scenario_version_id = scenario_v1.id
        apply_status_transition(
            simulation,
            target_status=SIMULATION_STATUS_READY_FOR_REVIEW,
            changed_at=datetime.now(UTC),
        )

        await db.commit()
        scenario_version_id = scenario_v1.id
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


__all__ = ["SCENARIO_GENERATION_JOB_TYPE", "handle_scenario_generation"]
