"""Application module for evaluations routes evaluations fit profile routes workflows."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluations.schemas.evaluations_schemas_evaluations_fit_profile_schema import (
    FitProfileGenerateResponse,
    FitProfileStatusResponse,
)
from app.evaluations.services import (
    evaluations_services_evaluations_fit_profile_api_service as fit_profile_api,
)
from app.shared.auth.shared_auth_current_user_utils import get_current_user
from app.shared.auth.shared_auth_roles_utils import ensure_recruiter
from app.shared.database import get_session
from app.shared.database.shared_database_models_model import User

router = APIRouter(prefix="/candidate_sessions", tags=["fit_profile"])


@router.post(
    "/{candidate_session_id}/fit_profile/generate",
    response_model=FitProfileGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate Fit Profile Route",
    description=(
        "Queue or compute fit-profile artifacts for a candidate session visible"
        " to the authenticated recruiter."
    ),
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Recruiter access required."},
        status.HTTP_404_NOT_FOUND: {"description": "Candidate session not found."},
    },
)
async def generate_fit_profile_route(
    candidate_session_id: Annotated[int, Path(..., ge=1)],
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> FitProfileGenerateResponse:
    """Handle the generate fit profile API route."""
    ensure_recruiter(user)
    payload = await fit_profile_api.generate_fit_profile(
        db,
        candidate_session_id=candidate_session_id,
        user=user,
    )
    return FitProfileGenerateResponse(**payload)


@router.get(
    "/{candidate_session_id}/fit_profile",
    response_model=FitProfileStatusResponse,
    response_model_exclude_unset=True,
    status_code=status.HTTP_200_OK,
    summary="Get Fit Profile Route",
    description=(
        "Return fit-profile generation status and latest report payload for a"
        " recruiter-visible candidate session."
    ),
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Recruiter access required."},
        status.HTTP_404_NOT_FOUND: {"description": "Candidate session not found."},
    },
)
async def get_fit_profile_route(
    candidate_session_id: Annotated[int, Path(..., ge=1)],
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> FitProfileStatusResponse:
    """Handle the get fit profile API route."""
    ensure_recruiter(user)
    payload = await fit_profile_api.fetch_fit_profile(
        db,
        candidate_session_id=candidate_session_id,
        user=user,
    )
    return FitProfileStatusResponse(**payload)


__all__ = ["router"]
