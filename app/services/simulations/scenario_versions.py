from __future__ import annotations

import copy
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.domains import Job, ScenarioVersion, Simulation, Task
from app.repositories.jobs import repository as jobs_repo
from app.repositories.scenario_versions import repository as scenario_repo
from app.repositories.scenario_versions.models import (
    SCENARIO_VERSION_STATUS_DRAFT,
    SCENARIO_VERSION_STATUS_GENERATING,
    SCENARIO_VERSION_STATUS_LOCKED,
    SCENARIO_VERSION_STATUS_READY,
)
from app.repositories.simulations.simulation import (
    SIMULATION_STATUS_ACTIVE_INVITING,
    SIMULATION_STATUS_READY_FOR_REVIEW,
)
from app.services.simulations.lifecycle import apply_status_transition
from app.services.simulations.scenario_generation import SCENARIO_GENERATION_JOB_TYPE
from app.services.simulations.scenario_payload_builder import (
    build_scenario_generation_payload,
)

logger = logging.getLogger(__name__)


def _default_storyline_md(simulation: Simulation) -> str:
    title = (simulation.title or "").strip()
    role = (simulation.role or "").strip()
    scenario_template = (simulation.scenario_template or "").strip()
    return (
        f"# {title}\n\n" f"Role: {role}\n" f"Template: {scenario_template}\n"
    ).strip()


def _task_prompts_payload(tasks: list[Task]) -> list[dict[str, Any]]:
    return [
        {
            "dayIndex": task.day_index,
            "type": task.type,
            "title": task.title,
            "description": task.description,
        }
        for task in sorted(tasks, key=lambda item: item.day_index)
    ]


def ensure_scenario_version_mutable(scenario_version: ScenarioVersion) -> None:
    if scenario_version.status != SCENARIO_VERSION_STATUS_LOCKED:
        return
    logger.warning(
        "Scenario mutation blocked because version is locked scenarioVersionId=%s simulationId=%s",
        scenario_version.id,
        scenario_version.simulation_id,
    )
    raise ApiError(
        status_code=status.HTTP_409_CONFLICT,
        detail="Scenario version is locked.",
        error_code="SCENARIO_LOCKED",
        retryable=False,
        details={},
        compact_response=True,
    )


async def create_initial_scenario_version(
    db: AsyncSession,
    *,
    simulation: Simulation,
    tasks: list[Task],
) -> ScenarioVersion:
    scenario_version = ScenarioVersion(
        simulation_id=simulation.id,
        version_index=1,
        status=SCENARIO_VERSION_STATUS_READY,
        storyline_md=_default_storyline_md(simulation),
        task_prompts_json=_task_prompts_payload(tasks),
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
    return await scenario_repo.get_active_for_simulation(db, simulation_id)


async def _require_owned_simulation_for_update(
    db: AsyncSession, simulation_id: int, actor_user_id: int
) -> Simulation:
    stmt = select(Simulation).where(Simulation.id == simulation_id).with_for_update()
    simulation = (await db.execute(stmt)).scalar_one_or_none()
    if simulation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found"
        )
    if simulation.created_by != actor_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this simulation",
        )
    return simulation


def _scenario_generation_idempotency_key(scenario_version_id: int) -> str:
    return f"scenario_version:{scenario_version_id}:scenario_generation"


async def lock_active_scenario_for_invites(
    db: AsyncSession,
    *,
    simulation_id: int,
    now: datetime | None = None,
) -> ScenarioVersion:
    lock_at = now or datetime.now(UTC)
    simulation = (
        await db.execute(
            select(Simulation).where(Simulation.id == simulation_id).with_for_update()
        )
    ).scalar_one_or_none()
    if simulation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found"
        )
    if simulation.active_scenario_version_id is None:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Simulation has no active scenario version.",
            error_code="SCENARIO_ACTIVE_VERSION_MISSING",
            retryable=False,
            details={},
        )
    active = await scenario_repo.get_by_id(
        db, simulation.active_scenario_version_id, for_update=True
    )
    if active is None or active.simulation_id != simulation.id:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Simulation has no active scenario version.",
            error_code="SCENARIO_ACTIVE_VERSION_MISSING",
            retryable=False,
            details={},
        )
    if active.status == SCENARIO_VERSION_STATUS_LOCKED:
        return active
    if active.status != SCENARIO_VERSION_STATUS_READY:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scenario version is not approved for inviting.",
            error_code="SCENARIO_NOT_READY",
            retryable=False,
            details={"status": active.status},
        )
    active.status = SCENARIO_VERSION_STATUS_LOCKED
    active.locked_at = lock_at
    logger.info(
        "Scenario version locked simulationId=%s scenarioVersionId=%s lockedAt=%s",
        simulation.id,
        active.id,
        active.locked_at.isoformat() if active.locked_at else None,
    )
    return active


async def regenerate_active_scenario_version(
    db: AsyncSession,
    *,
    simulation_id: int,
    actor_user_id: int,
) -> tuple[Simulation, ScenarioVersion]:
    simulation, regenerated, _job = await request_scenario_regeneration(
        db,
        simulation_id=simulation_id,
        actor_user_id=actor_user_id,
    )
    return simulation, regenerated


async def request_scenario_regeneration(
    db: AsyncSession,
    *,
    simulation_id: int,
    actor_user_id: int,
) -> tuple[Simulation, ScenarioVersion, Job]:
    regenerated_at = datetime.now(UTC)
    simulation = await _require_owned_simulation_for_update(
        db, simulation_id, actor_user_id
    )
    if simulation.active_scenario_version_id is None:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Simulation has no active scenario version.",
            error_code="SCENARIO_ACTIVE_VERSION_MISSING",
            retryable=False,
            details={},
        )
    if simulation.pending_scenario_version_id is not None:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scenario regeneration is already pending approval.",
            error_code="SCENARIO_REGENERATION_PENDING",
            retryable=False,
            details={
                "pendingScenarioVersionId": simulation.pending_scenario_version_id
            },
        )
    active = await scenario_repo.get_by_id(
        db, simulation.active_scenario_version_id, for_update=True
    )
    if active is None or active.simulation_id != simulation.id:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Simulation has no active scenario version.",
            error_code="SCENARIO_ACTIVE_VERSION_MISSING",
            retryable=False,
            details={},
        )

    new_index = await scenario_repo.next_version_index(db, simulation.id)
    regenerated = ScenarioVersion(
        simulation_id=simulation.id,
        version_index=new_index,
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
    db.add(regenerated)
    await db.flush()
    simulation.pending_scenario_version_id = regenerated.id
    apply_status_transition(
        simulation,
        target_status=SIMULATION_STATUS_READY_FOR_REVIEW,
        changed_at=regenerated_at,
    )
    payload_json = build_scenario_generation_payload(simulation)
    payload_json["scenarioVersionId"] = regenerated.id
    scenario_job = await jobs_repo.create_or_get_idempotent(
        db,
        job_type=SCENARIO_GENERATION_JOB_TYPE,
        idempotency_key=_scenario_generation_idempotency_key(regenerated.id),
        payload_json=payload_json,
        company_id=simulation.company_id,
        correlation_id=f"simulation:{simulation.id}:scenario_version:{regenerated.id}",
        commit=False,
    )
    await db.commit()
    await db.refresh(simulation)
    await db.refresh(regenerated)
    await db.refresh(scenario_job)
    logger.info(
        (
            "Scenario regeneration requested simulationId=%s fromScenarioVersionId=%s "
            "toScenarioVersionId=%s versionIndex=%s jobId=%s"
        ),
        simulation.id,
        active.id,
        regenerated.id,
        regenerated.version_index,
        scenario_job.id,
    )
    return simulation, regenerated, scenario_job


async def approve_scenario_version(
    db: AsyncSession,
    *,
    simulation_id: int,
    scenario_version_id: int,
    actor_user_id: int,
    now: datetime | None = None,
) -> tuple[Simulation, ScenarioVersion]:
    approved_at = now or datetime.now(UTC)
    simulation = await _require_owned_simulation_for_update(
        db, simulation_id, actor_user_id
    )
    target = await scenario_repo.get_by_id(db, scenario_version_id, for_update=True)
    if target is None or target.simulation_id != simulation.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario version not found",
        )

    pending_id = simulation.pending_scenario_version_id
    if pending_id is None:
        if simulation.active_scenario_version_id == target.id:
            apply_status_transition(
                simulation,
                target_status=SIMULATION_STATUS_ACTIVE_INVITING,
                changed_at=approved_at,
            )
            await db.commit()
            await db.refresh(simulation)
            await db.refresh(target)
            return simulation, target
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="No pending scenario version to approve.",
            error_code="SCENARIO_APPROVAL_NOT_PENDING",
            retryable=False,
            details={},
        )
    if pending_id != target.id:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scenario version is not pending approval.",
            error_code="SCENARIO_VERSION_NOT_PENDING",
            retryable=False,
            details={"pendingScenarioVersionId": pending_id},
        )
    if target.status != SCENARIO_VERSION_STATUS_READY:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scenario version is not ready for approval.",
            error_code="SCENARIO_NOT_READY",
            retryable=False,
            details={"status": target.status},
        )

    simulation.active_scenario_version_id = target.id
    simulation.pending_scenario_version_id = None
    apply_status_transition(
        simulation,
        target_status=SIMULATION_STATUS_ACTIVE_INVITING,
        changed_at=approved_at,
    )
    await db.commit()
    await db.refresh(simulation)
    await db.refresh(target)
    logger.info(
        (
            "Scenario version approved simulationId=%s actorUserId=%s "
            "scenarioVersionId=%s status=%s"
        ),
        simulation.id,
        actor_user_id,
        target.id,
        simulation.status,
    )
    return simulation, target


async def update_active_scenario_version(
    db: AsyncSession,
    *,
    simulation_id: int,
    actor_user_id: int,
    updates: dict[str, Any],
) -> ScenarioVersion:
    simulation = await _require_owned_simulation_for_update(
        db, simulation_id, actor_user_id
    )
    if simulation.active_scenario_version_id is None:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Simulation has no active scenario version.",
            error_code="SCENARIO_ACTIVE_VERSION_MISSING",
            retryable=False,
            details={},
        )
    active = await scenario_repo.get_by_id(
        db, simulation.active_scenario_version_id, for_update=True
    )
    if active is None or active.simulation_id != simulation.id:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Simulation has no active scenario version.",
            error_code="SCENARIO_ACTIVE_VERSION_MISSING",
            retryable=False,
            details={},
        )

    ensure_scenario_version_mutable(active)
    if "storyline_md" in updates:
        active.storyline_md = str(updates["storyline_md"] or "")
    if "task_prompts_json" in updates:
        active.task_prompts_json = (
            [] if updates["task_prompts_json"] is None else updates["task_prompts_json"]
        )
    if "rubric_json" in updates:
        active.rubric_json = (
            {} if updates["rubric_json"] is None else updates["rubric_json"]
        )
    if "focus_notes" in updates:
        active.focus_notes = str(updates["focus_notes"] or "")
    if "status" in updates:
        next_status = str(updates["status"])
        if next_status not in {
            SCENARIO_VERSION_STATUS_DRAFT,
            SCENARIO_VERSION_STATUS_READY,
        }:
            raise ApiError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid scenario status.",
                error_code="SCENARIO_STATUS_INVALID",
                retryable=False,
                details={
                    "allowed": [
                        SCENARIO_VERSION_STATUS_DRAFT,
                        SCENARIO_VERSION_STATUS_READY,
                    ]
                },
            )
        active.status = next_status
    await db.commit()
    await db.refresh(active)
    logger.info(
        "Scenario version updated simulationId=%s scenarioVersionId=%s status=%s",
        simulation.id,
        active.id,
        active.status,
    )
    return active


__all__ = [
    "approve_scenario_version",
    "create_initial_scenario_version",
    "ensure_scenario_version_mutable",
    "get_active_scenario_version",
    "lock_active_scenario_for_invites",
    "regenerate_active_scenario_version",
    "request_scenario_regeneration",
    "update_active_scenario_version",
]
