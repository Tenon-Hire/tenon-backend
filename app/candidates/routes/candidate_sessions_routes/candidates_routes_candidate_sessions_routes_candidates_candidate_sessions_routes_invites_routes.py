"""Application module for candidates routes candidate sessions routes candidates candidate sessions routes invites routes workflows."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions import services as cs_service
from app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_rate_limits_routes import (
    CANDIDATE_INVITES_RATE_LIMIT,
)
from app.candidates.schemas.candidates_schemas_candidates_candidate_sessions_core_schema import (
    CandidateInviteListItem,
)
from app.shared.auth import rate_limit
from app.shared.auth.principal import Principal
from app.shared.auth.shared_auth_candidate_access_utils import (
    require_candidate_principal,
)
from app.shared.database import get_session

router = APIRouter()


@router.get("/invites", response_model=list[CandidateInviteListItem])
async def list_candidate_invites(
    request: Request,
    principal: Annotated[Principal, Depends(require_candidate_principal)],
    db: Annotated[AsyncSession, Depends(get_session)],
    includeTerminated: bool = False,
) -> list[CandidateInviteListItem]:
    """List all invites for the authenticated candidate email."""
    if rate_limit.rate_limit_enabled():
        key = rate_limit.rate_limit_key(
            "candidate_invites",
            rate_limit.hash_value(principal.sub),
            rate_limit.client_id(request),
        )
        rate_limit.limiter.allow(key, CANDIDATE_INVITES_RATE_LIMIT)
    if includeTerminated:
        return await cs_service.invite_list_for_principal(
            db, principal, include_terminated=True
        )
    return await cs_service.invite_list_for_principal(db, principal)
