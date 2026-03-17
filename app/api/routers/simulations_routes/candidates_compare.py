from __future__ import annotations

import logging
from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.current_user import get_current_user
from app.core.auth.roles import ensure_recruiter
from app.core.db import get_session
from app.domains import User
from app.domains.simulations import service as sim_service
from app.schemas.simulations_compare import SimulationCandidatesCompareResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/{simulation_id}/candidates/compare",
    response_model=SimulationCandidatesCompareResponse,
    status_code=status.HTTP_200_OK,
)
async def list_simulation_candidates_compare(
    simulation_id: Annotated[int, Path(..., ge=1)],
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> SimulationCandidatesCompareResponse:
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
