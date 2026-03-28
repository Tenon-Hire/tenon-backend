"""Application module for candidates routes candidate sessions routes candidates candidate sessions routes resolve routes workflows."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_claim_logic_routes import (
    claim_token,
)
from app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_responses_routes import (
    render_claim_response,
)
from app.candidates.schemas.candidates_schemas_candidates_candidate_sessions_core_schema import (
    CandidateSessionResolveResponse,
)
from app.shared.auth.principal import Principal
from app.shared.auth.shared_auth_candidate_access_utils import (
    require_candidate_principal,
)
from app.shared.database import get_session

router = APIRouter()


@router.get("/session/{token}", response_model=CandidateSessionResolveResponse)
async def resolve_candidate_session(
    token: Annotated[str, Path(..., min_length=20, max_length=255)],
    request: Request,
    principal: Annotated[Principal, Depends(require_candidate_principal)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> CandidateSessionResolveResponse:
    """Claim an invite token for the authenticated candidate."""
    return render_claim_response(await claim_token(token, request, principal, db))


@router.post(
    "/session/{token}/claim",
    response_model=CandidateSessionResolveResponse,
    status_code=status.HTTP_200_OK,
)
async def claim_candidate_session(
    token: Annotated[str, Path(..., min_length=20, max_length=255)],
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(require_candidate_principal)],
) -> CandidateSessionResolveResponse:
    """Idempotent claim endpoint for authenticated candidates (no email body required)."""
    return render_claim_response(await claim_token(token, request, principal, db))
