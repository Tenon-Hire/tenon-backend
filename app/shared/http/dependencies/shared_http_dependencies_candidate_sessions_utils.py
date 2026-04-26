"""Application module for http dependencies candidate sessions utils workflows."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions import services as cs_service
from app.shared.auth.principal import Principal
from app.shared.auth.shared_auth_candidate_access_utils import (
    require_candidate_principal,
)
from app.shared.database import get_session
from app.shared.database.shared_database_models_model import CandidateSession
from app.shared.time.shared_time_now_service import utcnow as shared_utcnow
from app.shared.utils.shared_utils_errors_utils import ApiError


async def candidate_session_from_headers(
    principal: Annotated[Principal, Depends(require_candidate_principal)],
    x_candidate_session_id: Annotated[
        int | None, Header(alias="x-candidate-session-id", ge=1)
    ] = None,
    db: Annotated[AsyncSession, Depends(get_session)] = None,
) -> CandidateSession:
    """Load a candidate session for the authenticated candidate."""
    if x_candidate_session_id is None:
        raise ApiError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing candidate session headers",
            error_code="CANDIDATE_SESSION_HEADER_REQUIRED",
        )
    return await cs_service.fetch_owned_session(
        db, int(x_candidate_session_id), principal, now=shared_utcnow()
    )
