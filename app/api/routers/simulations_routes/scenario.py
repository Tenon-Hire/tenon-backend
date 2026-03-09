from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers.simulations_routes.rate_limits import (
    enforce_scenario_regenerate_limit,
)
from app.core.auth.current_user import get_current_user
from app.core.auth.roles import ensure_recruiter_or_none
from app.core.db import get_session
from app.domains.simulations import service as sim_service
from app.domains.simulations.schemas import (
    ScenarioActiveUpdateRequest,
    ScenarioActiveUpdateResponse,
    ScenarioApproveResponse,
    ScenarioRegenerateResponse,
    ScenarioStateSummary,
)

router = APIRouter()


@router.post(
    "/{simulation_id}/scenario/regenerate",
    response_model=ScenarioRegenerateResponse,
    status_code=status.HTTP_200_OK,
)
async def regenerate_scenario_version(
    simulation_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    ensure_recruiter_or_none(user)
    enforce_scenario_regenerate_limit(request, user.id)
    (
        _simulation,
        scenario_version,
        scenario_job,
    ) = await sim_service.request_scenario_regeneration(
        db,
        simulation_id=simulation_id,
        actor_user_id=user.id,
    )
    return ScenarioRegenerateResponse(
        scenarioVersionId=scenario_version.id,
        jobId=scenario_job.id,
        status=scenario_version.status,
    )


@router.post(
    "/{simulation_id}/scenario/{scenario_version_id}/approve",
    response_model=ScenarioApproveResponse,
    status_code=status.HTTP_200_OK,
)
async def approve_scenario_version(
    simulation_id: int,
    scenario_version_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    ensure_recruiter_or_none(user)
    simulation, scenario_version = await sim_service.approve_scenario_version(
        db,
        simulation_id=simulation_id,
        scenario_version_id=scenario_version_id,
        actor_user_id=user.id,
    )
    return ScenarioApproveResponse(
        simulationId=simulation.id,
        status=sim_service.normalize_simulation_status_or_raise(simulation.status),
        activeScenarioVersionId=(
            simulation.active_scenario_version_id or scenario_version.id
        ),
        pendingScenarioVersionId=simulation.pending_scenario_version_id,
        scenario=ScenarioStateSummary(
            id=scenario_version.id,
            versionIndex=scenario_version.version_index,
            status=scenario_version.status,
            lockedAt=scenario_version.locked_at,
        ),
    )


@router.patch(
    "/{simulation_id}/scenario/active",
    response_model=ScenarioActiveUpdateResponse,
    status_code=status.HTTP_200_OK,
)
async def update_active_scenario_version(
    simulation_id: int,
    payload: ScenarioActiveUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    ensure_recruiter_or_none(user)
    updates = payload.model_dump(exclude_unset=True)
    field_map = {
        "storylineMd": "storyline_md",
        "taskPromptsJson": "task_prompts_json",
        "rubricJson": "rubric_json",
        "focusNotes": "focus_notes",
        "status": "status",
    }
    normalized_updates = {
        mapped_name: updates[field_name]
        for field_name, mapped_name in field_map.items()
        if field_name in updates
    }
    scenario_version = await sim_service.update_active_scenario_version(
        db,
        simulation_id=simulation_id,
        actor_user_id=user.id,
        updates=normalized_updates,
    )
    return ScenarioActiveUpdateResponse(
        simulationId=simulation_id,
        scenario=ScenarioStateSummary(
            id=scenario_version.id,
            versionIndex=scenario_version.version_index,
            status=scenario_version.status,
            lockedAt=scenario_version.locked_at,
        ),
    )


__all__ = [
    "approve_scenario_version",
    "regenerate_scenario_version",
    "router",
    "update_active_scenario_version",
]
