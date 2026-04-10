"""Application module for evaluations routes evaluations winoe report routes workflows."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluations.schemas.evaluations_schemas_evaluations_winoe_report_schema import (
    WinoeReportGenerateResponse,
    WinoeReportStatusResponse,
)
from app.evaluations.services import (
    evaluations_services_evaluations_winoe_report_api_service as winoe_report_api,
)
from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_talent_partner
from app.shared.database import get_session
from app.shared.database.shared_database_models_model import User

router = APIRouter(prefix="/candidate_sessions", tags=["winoe_report"])


@router.post(
    "/{candidate_session_id}/winoe_report/generate",
    response_model=WinoeReportGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate Winoe Report Route",
    description=(
        "Queue or compute winoe-report artifacts for a candidate session visible"
        " to the authenticated Talent Partner."
    ),
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Talent Partner access required."},
        status.HTTP_404_NOT_FOUND: {"description": "Candidate session not found."},
    },
)
async def generate_winoe_report_route(
    candidate_session_id: Annotated[int, Path(..., ge=1)],
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> WinoeReportGenerateResponse:
    """Handle the generate winoe report API route."""
    ensure_talent_partner(user)
    payload = await winoe_report_api.generate_winoe_report(
        db,
        candidate_session_id=candidate_session_id,
        user=user,
    )
    return WinoeReportGenerateResponse(**payload)


@router.get(
    "/{candidate_session_id}/winoe_report",
    response_model=WinoeReportStatusResponse,
    response_model_exclude_unset=True,
    status_code=status.HTTP_200_OK,
    summary="Get Winoe Report Route",
    description=(
        "Return winoe-report generation status and latest report payload for a"
        " Talent Partner-visible candidate session."
    ),
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Talent Partner access required."},
        status.HTTP_404_NOT_FOUND: {"description": "Candidate session not found."},
    },
)
async def get_winoe_report_route(
    candidate_session_id: Annotated[int, Path(..., ge=1)],
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> WinoeReportStatusResponse:
    """Handle the get winoe report API route."""
    ensure_talent_partner(user)
    payload = await winoe_report_api.fetch_winoe_report(
        db,
        candidate_session_id=candidate_session_id,
        user=user,
    )
    return WinoeReportStatusResponse(**payload)


__all__ = ["router"]
