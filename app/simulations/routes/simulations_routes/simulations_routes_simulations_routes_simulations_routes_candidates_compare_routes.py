"""Application module for simulations routes simulations routes simulations routes candidates compare routes workflows."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_recruiter
from app.shared.database import get_session
from app.shared.database.shared_database_models_model import User
from app.simulations import services as sim_service
from app.simulations.schemas.simulations_schemas_simulations_compare_schema import (
    SimulationCandidatesCompareResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/{simulation_id}/candidates/compare",
    response_model=SimulationCandidatesCompareResponse,
    status_code=status.HTTP_200_OK,
    summary="List Simulation Candidates Compare",
    description=(
        "Return side-by-side candidate progress and scoring signals for a"
        " recruiter-owned simulation."
    ),
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Recruiter access required."},
        status.HTTP_404_NOT_FOUND: {"description": "Simulation not found."},
    },
)
async def list_simulation_candidates_compare(
    simulation_id: Annotated[int, Path(..., ge=1)],
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> SimulationCandidatesCompareResponse:
    """Return simulation candidates compare."""
    ensure_recruiter(user)
    started_at = perf_counter()
    payload = await sim_service.list_candidates_compare_summary(
        db,
        simulation_id=simulation_id,
        user=user,
    )
    latency_ms = int((perf_counter() - started_at) * 1000)
    logger.info(
        "Simulation candidates compare fetched simulationId=%s recruiterId=%s rowCount=%s latencyMs=%s",
        simulation_id,
        user.id,
        len(payload["candidates"]),
        latency_ms,
    )
    return SimulationCandidatesCompareResponse(**payload)


__all__ = ["router", "list_simulation_candidates_compare"]
