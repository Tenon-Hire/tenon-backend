from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers.simulations_routes.detail_render import render_simulation_detail
from app.core.auth.current_user import get_current_user
from app.core.auth.roles import ensure_recruiter_or_none
from app.core.db import get_session
from app.domains.simulations import service as sim_service
from app.domains.simulations.schemas import SimulationDetailResponse, SimulationUpdate

router = APIRouter()


@router.put(
    "/{simulation_id}",
    response_model=SimulationDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def update_simulation(
    simulation_id: int,
    payload: SimulationUpdate,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    """Update mutable simulation configuration."""
    ensure_recruiter_or_none(user)
    simulation, tasks = await sim_service.update_simulation(
        db,
        simulation_id=simulation_id,
        actor_user_id=user.id,
        payload=payload,
    )
    active_scenario_version = await sim_service.get_active_scenario_version(
        db,
        simulation_id,
    )
    return render_simulation_detail(simulation, tasks, active_scenario_version)


__all__ = ["router", "update_simulation"]
