"""Application module for simulations routes simulations routes simulations routes invite create routes workflows."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.schemas.candidates_schemas_candidates_candidate_sessions_core_schema import (
    CandidateInviteErrorResponse,
    CandidateInviteRequest,
    CandidateInviteResponse,
)
from app.integrations.github import GithubClient
from app.notifications.services.notifications_services_notifications_email_sender_service import (
    EmailService,
)
from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_recruiter_or_none
from app.shared.database import get_session
from app.shared.http.dependencies.shared_http_dependencies_github_native_utils import (
    get_github_client,
)
from app.shared.http.dependencies.shared_http_dependencies_notifications_utils import (
    get_email_service,
)
from app.simulations.routes.simulations_routes.simulations_routes_simulations_routes_simulations_routes_invite_create_logic_routes import (
    create_invite_response,
)

router = APIRouter()


@router.post(
    "/{simulation_id}/invite",
    response_model=CandidateInviteResponse,
    status_code=status.HTTP_200_OK,
    responses={status.HTTP_409_CONFLICT: {"model": CandidateInviteErrorResponse}},
)
async def create_candidate_invite(
    simulation_id: int,
    payload: CandidateInviteRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[Any, Depends(get_current_user)],
    email_service: Annotated[EmailService, Depends(get_email_service)],
    github_client: Annotated[GithubClient, Depends(get_github_client)],
):
    """Create a candidate_session invite token for a simulation (recruiter-only)."""
    ensure_recruiter_or_none(user)
    return await create_invite_response(
        db,
        simulation_id=simulation_id,
        payload=payload,
        user_id=user.id,
        request=request,
        email_service=email_service,
        github_client=github_client,
    )
