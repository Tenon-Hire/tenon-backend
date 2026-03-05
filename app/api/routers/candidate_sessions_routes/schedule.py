from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.notifications import get_email_service
from app.api.routers.candidate_sessions_routes.responses import render_schedule_response
from app.core.auth.candidate_access import require_candidate_principal
from app.core.auth.principal import Principal
from app.core.db import get_session
from app.domains.candidate_sessions import service as cs_service
from app.domains.candidate_sessions.schemas import (
    CandidateSessionScheduleRequest,
    CandidateSessionScheduleResponse,
)
from app.services.email import EmailService

router = APIRouter()


@router.post(
    "/session/{token}/schedule",
    response_model=CandidateSessionScheduleResponse,
)
async def schedule_candidate_session(
    token: Annotated[str, Path(..., min_length=20, max_length=255)],
    payload: CandidateSessionScheduleRequest,
    request: Request,
    principal: Annotated[Principal, Depends(require_candidate_principal)],
    db: Annotated[AsyncSession, Depends(get_session)],
    email_service: Annotated[EmailService, Depends(get_email_service)],
) -> CandidateSessionScheduleResponse:
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
