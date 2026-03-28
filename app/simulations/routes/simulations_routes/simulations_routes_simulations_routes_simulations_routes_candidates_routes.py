"""Application module for simulations routes simulations routes simulations routes candidates routes workflows."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.schemas.candidates_schemas_candidates_candidate_sessions_core_schema import (
    CandidateSessionListItem,
)
from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_recruiter_or_none
from app.shared.database import get_session
from app.simulations import services as sim_service

router = APIRouter()


@router.get(
    "/{simulation_id}/candidates",
    response_model=list[CandidateSessionListItem],
    status_code=status.HTTP_200_OK,
)
async def list_simulation_candidates(
    simulation_id: int,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
    includeTerminated: bool = False,
):
    """List candidate sessions for a simulation (recruiter-only)."""
    ensure_recruiter_or_none(user)
    await sim_service.require_owned_simulation(
        db,
        simulation_id,
        user.id,
        include_terminated=includeTerminated,
    )
    rows = await sim_service.list_candidates_with_profile(db, simulation_id)
    return [
        CandidateSessionListItem(
            candidateSessionId=cs.id,
            inviteEmail=cs.invite_email,
            candidateName=cs.candidate_name,
            status=cs.status,
            startedAt=cs.started_at,
            completedAt=cs.completed_at,
            hasFitProfile=(profile_id is not None),
            inviteEmailStatus=getattr(cs, "invite_email_status", None),
            inviteEmailSentAt=getattr(cs, "invite_email_sent_at", None),
            inviteEmailError=getattr(cs, "invite_email_error", None),
        )
        for cs, profile_id in rows
    ]
