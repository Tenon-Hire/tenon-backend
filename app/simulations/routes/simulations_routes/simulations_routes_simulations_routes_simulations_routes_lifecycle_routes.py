"""Application module for simulations routes simulations routes simulations routes lifecycle routes workflows."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_recruiter_or_none
from app.shared.database import get_session
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.simulations import services as sim_service
from app.simulations.schemas.simulations_schemas_simulations_core_schema import (
    SimulationActivateResponse,
    SimulationLifecycleRequest,
    SimulationTerminateResponse,
)

router = APIRouter()


def _require_confirmation(payload: SimulationLifecycleRequest) -> None:
    if payload.confirm:
        return
    raise ApiError(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="confirm=true is required",
        error_code="SIMULATION_CONFIRMATION_REQUIRED",
        retryable=False,
        details={},
    )


@router.post(
    "/{simulation_id}/activate",
    response_model=SimulationActivateResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate Simulation",
    description=(
        "Transition a simulation into the active state once recruiter confirms"
        " readiness."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Activation confirmation missing."
        },
        status.HTTP_403_FORBIDDEN: {"description": "Recruiter access required."},
        status.HTTP_404_NOT_FOUND: {"description": "Simulation not found."},
    },
)
async def activate_simulation(
    simulation_id: int,
    payload: SimulationLifecycleRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    """Activate simulation."""
    ensure_recruiter_or_none(user)
    _require_confirmation(payload)
    simulation = await sim_service.activate_simulation(
        db, simulation_id=simulation_id, actor_user_id=user.id
    )
    status_value = sim_service.normalize_simulation_status_or_raise(simulation.status)
    return SimulationActivateResponse(
        simulationId=simulation.id,
        status=status_value,
        activatedAt=simulation.activated_at,
    )


@router.post(
    "/{simulation_id}/terminate",
    response_model=SimulationTerminateResponse,
    status_code=status.HTTP_200_OK,
    summary="Terminate Simulation",
    description=(
        "Terminate an active simulation and enqueue workspace cleanup jobs for"
        " associated candidate workspaces."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Termination confirmation missing."
        },
        status.HTTP_403_FORBIDDEN: {"description": "Recruiter access required."},
        status.HTTP_404_NOT_FOUND: {"description": "Simulation not found."},
    },
)
async def terminate_simulation(
    simulation_id: int,
    payload: SimulationLifecycleRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    """Terminate simulation."""
    ensure_recruiter_or_none(user)
    _require_confirmation(payload)
    terminated = await sim_service.terminate_simulation_with_cleanup(
        db,
        simulation_id=simulation_id,
        actor_user_id=user.id,
        reason=payload.reason,
    )
    simulation = terminated.simulation
    status_value = sim_service.normalize_simulation_status_or_raise(simulation.status)
    return SimulationTerminateResponse(
        simulationId=simulation.id,
        status=status_value,
        terminatedAt=simulation.terminated_at,
        cleanupJobIds=terminated.cleanup_job_ids,
    )
