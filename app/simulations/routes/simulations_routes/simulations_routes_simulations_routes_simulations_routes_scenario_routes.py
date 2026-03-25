from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_recruiter_or_none
from app.shared.database import get_session
from app.simulations import services as sim_service
from app.simulations.routes.simulations_routes.simulations_routes_simulations_routes_simulations_routes_rate_limits_routes import (
    enforce_scenario_regenerate_limit,
)
from app.simulations.routes.simulations_routes.simulations_routes_simulations_routes_simulations_routes_scenario_payloads_routes import (
    build_active_update_response,
    build_approve_response,
    build_patch_response,
    build_regenerate_response,
    normalize_active_updates,
    normalize_patch_updates,
)
from app.simulations.schemas.simulations_schemas_simulations_core_schema import (
    ScenarioActiveUpdateRequest,
    ScenarioActiveUpdateResponse,
    ScenarioApproveResponse,
    ScenarioRegenerateResponse,
    ScenarioVersionPatchRequest,
    ScenarioVersionPatchResponse,
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
    return build_regenerate_response(scenario_version, scenario_job)


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
    return build_approve_response(simulation, scenario_version)


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
    scenario_version = await sim_service.update_active_scenario_version(
        db,
        simulation_id=simulation_id,
        actor_user_id=user.id,
        updates=normalize_active_updates(payload),
    )
    return build_active_update_response(simulation_id, scenario_version)


@router.patch(
    "/{simulation_id}/scenario/{scenario_version_id}",
    response_model=ScenarioVersionPatchResponse,
    status_code=status.HTTP_200_OK,
)
async def patch_scenario_version(
    simulation_id: int,
    scenario_version_id: int,
    payload: ScenarioVersionPatchRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    ensure_recruiter_or_none(user)
    scenario_version = await sim_service.patch_scenario_version(
        db,
        simulation_id=simulation_id,
        scenario_version_id=scenario_version_id,
        actor_user_id=user.id,
        updates=normalize_patch_updates(payload),
    )
    return build_patch_response(scenario_version)


__all__ = [
    "approve_scenario_version",
    "patch_scenario_version",
    "regenerate_scenario_version",
    "router",
    "update_active_scenario_version",
]
