from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.current_user import get_current_user
from app.core.auth.roles import ensure_recruiter
from app.core.db import get_session
from app.domains import User
from app.schemas.fit_profile import (
    FitProfileGenerateResponse,
    FitProfileStatusResponse,
)
from app.services.evaluations import fit_profile_api

router = APIRouter(prefix="/candidate_sessions", tags=["fit_profile"])


@router.post(
    "/{candidate_session_id}/fit_profile/generate",
    response_model=FitProfileGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_fit_profile_route(
    candidate_session_id: Annotated[int, Path(..., ge=1)],
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> FitProfileGenerateResponse:
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
)
async def get_fit_profile_route(
    candidate_session_id: Annotated[int, Path(..., ge=1)],
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> FitProfileStatusResponse:
    ensure_recruiter(user)
    payload = await fit_profile_api.fetch_fit_profile(
        db,
        candidate_session_id=candidate_session_id,
        user=user,
    )
    return FitProfileStatusResponse(**payload)


__all__ = ["router"]
