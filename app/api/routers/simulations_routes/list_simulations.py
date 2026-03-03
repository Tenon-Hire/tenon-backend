from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.current_user import get_current_user
from app.core.auth.roles import ensure_recruiter_or_none
from app.core.db import get_session
from app.domains.simulations import service as sim_service
from app.domains.simulations.schemas import ScenarioVersionSummary, SimulationListItem

router = APIRouter(prefix="/simulations")


@router.get("", response_model=list[SimulationListItem], status_code=status.HTTP_200_OK)
async def list_simulations(
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
    includeTerminated: bool = False,
):
    """List simulations for recruiter dashboard (scoped to current user)."""
    ensure_recruiter_or_none(user)
    rows = await sim_service.list_simulations(
        db, user.id, include_terminated=includeTerminated
    )
    return [
        SimulationListItem(
            id=sim.id,
            title=sim.title,
            role=sim.role,
            techStack=sim.tech_stack,
            templateKey=sim.template_key,
            status=sim_service.normalize_simulation_status_or_raise(
                getattr(sim, "status", None)
            ),
            activatedAt=getattr(sim, "activated_at", None),
            terminatedAt=getattr(sim, "terminated_at", None),
            scenarioVersionSummary=ScenarioVersionSummary(
                templateKey=getattr(sim, "template_key", None),
                scenarioTemplate=getattr(sim, "scenario_template", None),
            ),
            createdAt=sim.created_at,
            numCandidates=int(num_candidates),
        )
        for sim, num_candidates in rows
    ]
