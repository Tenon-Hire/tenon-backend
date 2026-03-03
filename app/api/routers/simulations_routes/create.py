from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.current_user import get_current_user
from app.core.auth.roles import ensure_recruiter_or_none
from app.core.db import get_session
from app.core.errors import ApiError
from app.domains.simulations import service as sim_service
from app.domains.simulations.schemas import (
    ScenarioVersionSummary,
    SimulationCreate,
    SimulationCreateResponse,
    TaskOut,
)

router = APIRouter(prefix="/simulations")


def _normalized_status_or_error(raw_status: str | None) -> str:
    normalized = sim_service.normalize_simulation_status(raw_status)
    if normalized is not None:
        return normalized
    raise ApiError(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Invalid simulation status.",
        error_code="SIMULATION_STATUS_INVALID",
        retryable=False,
        details={"status": raw_status},
    )


@router.post(
    "", response_model=SimulationCreateResponse, status_code=status.HTTP_201_CREATED
)
async def create_simulation(
    payload: SimulationCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    """Create a simulation and seed default tasks."""
    ensure_recruiter_or_none(user)
    sim, created_tasks = await sim_service.create_simulation_with_tasks(
        db, payload, user
    )
    raw_status = getattr(sim, "status", None)
    return SimulationCreateResponse(
        id=sim.id,
        title=sim.title,
        role=sim.role,
        techStack=sim.tech_stack,
        seniority=sim.seniority,
        focus=sim.focus,
        templateKey=sim.template_key,
        status=_normalized_status_or_error(raw_status),
        generatingAt=getattr(sim, "generating_at", None),
        readyForReviewAt=getattr(sim, "ready_for_review_at", None),
        activatedAt=getattr(sim, "activated_at", None),
        terminatedAt=getattr(sim, "terminated_at", None),
        scenarioVersionSummary=ScenarioVersionSummary(
            templateKey=getattr(sim, "template_key", None),
            scenarioTemplate=getattr(sim, "scenario_template", None),
        ),
        tasks=[
            TaskOut(id=t.id, day_index=t.day_index, type=t.type, title=t.title)
            for t in created_tasks
        ],
    )
