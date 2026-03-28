"""Application module for candidates routes candidate sessions routes candidates candidate sessions routes schedule routes workflows."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions import services as cs_service
from app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_responses_routes import (
    render_schedule_response,
)
from app.candidates.schemas.candidates_schemas_candidates_candidate_sessions_core_schema import (
    CandidateSessionScheduleRequest,
    CandidateSessionScheduleResponse,
)
from app.notifications.services.notifications_services_notifications_email_sender_service import (
    EmailService,
)
from app.shared.auth.principal import Principal
from app.shared.auth.shared_auth_candidate_access_utils import (
    require_candidate_principal,
)
from app.shared.database import get_session
from app.shared.http.dependencies.shared_http_dependencies_notifications_utils import (
    get_email_service,
)

router = APIRouter()


@router.post(
    "/session/{token}/schedule",
    response_model=CandidateSessionScheduleResponse,
    summary="Schedule Candidate Session",
    description=(
        "Persist candidate-proposed schedule details and send confirmation"
        " notifications for the session token."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Candidate authentication required."
        },
        status.HTTP_403_FORBIDDEN: {"description": "Token does not match principal."},
        status.HTTP_404_NOT_FOUND: {"description": "Candidate session not found."},
        status.HTTP_410_GONE: {"description": "Candidate invite token is expired."},
    },
)
async def schedule_candidate_session(
    token: Annotated[str, Path(..., min_length=20, max_length=255)],
    payload: CandidateSessionScheduleRequest,
    request: Request,
    principal: Annotated[Principal, Depends(require_candidate_principal)],
    db: Annotated[AsyncSession, Depends(get_session)],
    email_service: Annotated[EmailService, Depends(get_email_service)],
) -> CandidateSessionScheduleResponse:
    """Schedule candidate session."""
    correlation_id = (
        request.headers.get("x-correlation-id")
        or request.headers.get("x-request-id")
        or None
    )
    result = await cs_service.schedule_candidate_session(
        db,
        token=token,
        principal=principal,
        scheduled_start_at=payload.scheduledStartAt,
        candidate_timezone=payload.candidateTimezone,
        email_service=email_service,
        correlation_id=correlation_id,
    )
    return render_schedule_response(result.candidate_session)


__all__ = ["schedule_candidate_session", "router"]
