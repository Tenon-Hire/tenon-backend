"""Application module for simulations routes simulations routes simulations routes update routes workflows."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_recruiter_or_none
from app.shared.database import get_session
from app.simulations import services as sim_service
from app.simulations.routes.simulations_routes.simulations_routes_simulations_routes_simulations_routes_detail_render_routes import (
    render_simulation_detail,
)
from app.simulations.schemas.simulations_schemas_simulations_core_schema import (
    SimulationDetailResponse,
    SimulationUpdate,
)

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
