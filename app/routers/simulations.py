from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas.candidate_session import (
    CandidateInviteRequest,
    CandidateInviteResponse,
    CandidateSessionListItem,
)
from app.schemas.simulation import (
    SimulationCreate,
    SimulationCreateResponse,
    SimulationListItem,
    TaskOut,
)
from app.security.current_user import get_current_user
from app.security.roles import ensure_recruiter
from app.services import simulations as sim_service

router = APIRouter()

INVITE_TOKEN_TTL_DAYS = 14


@router.get("", response_model=list[SimulationListItem], status_code=status.HTTP_200_OK)
async def list_simulations(
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    """List simulations for recruiter dashboard (scoped to current user)."""
    ensure_recruiter(user, allow_none=True)
    rows = await sim_service.list_simulations(db, user.id)

    return [
        SimulationListItem(
            id=sim.id,
            title=sim.title,
            role=sim.role,
            techStack=sim.tech_stack,
            createdAt=sim.created_at,
            numCandidates=int(num_candidates),
        )
        for sim, num_candidates in rows
    ]


@router.post(
    "", response_model=SimulationCreateResponse, status_code=status.HTTP_201_CREATED
)
async def create_simulation(
    payload: SimulationCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    """Create a simulation and seed default tasks."""
    ensure_recruiter(user, allow_none=True)

    sim, created_tasks = await sim_service.create_simulation_with_tasks(
        db, payload, user
    )

    return SimulationCreateResponse(
        id=sim.id,
        title=sim.title,
        role=sim.role,
        techStack=sim.tech_stack,
        seniority=sim.seniority,
        focus=sim.focus,
        tasks=[
            TaskOut(id=t.id, day_index=t.day_index, type=t.type, title=t.title)
            for t in created_tasks
        ],
    )


@router.post(
    "/{simulation_id}/invite",
    response_model=CandidateInviteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_candidate_invite(
    simulation_id: int,
    payload: CandidateInviteRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    """Create a candidate_session invite token for a simulation (recruiter-only)."""
    ensure_recruiter(user, allow_none=True)

    await sim_service.require_owned_simulation(db, simulation_id, user.id)
    cs = await sim_service.create_invite(
        db, simulation_id, payload, now=datetime.now(UTC)
    )
    return CandidateInviteResponse(
        candidateSessionId=cs.id,
        token=cs.token,
        inviteUrl=sim_service.invite_url(cs.token),
    )


@router.get(
    "/{simulation_id}/candidates",
    response_model=list[CandidateSessionListItem],
    status_code=status.HTTP_200_OK,
)
async def list_simulation_candidates(
    simulation_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
):
    """List candidate sessions for a simulation (recruiter-only)."""
    ensure_recruiter(user, allow_none=True)

    await sim_service.require_owned_simulation(db, simulation_id, user.id)
    rows = await sim_service.list_candidates_with_profile(db, simulation_id)

    return [
        CandidateSessionListItem(
            candidateSessionId=cs.id,
            inviteEmail=cs.invite_email,
            candidateName=cs.candidate_name,
            status=cs.status,
            startedAt=cs.started_at,
            completedAt=cs.completed_at,
            hasReport=(profile_id is not None),
        )
        for cs, profile_id in rows
    ]
