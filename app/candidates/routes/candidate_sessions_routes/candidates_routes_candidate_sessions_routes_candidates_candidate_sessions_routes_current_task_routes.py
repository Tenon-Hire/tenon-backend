"""Application module for candidates routes candidate sessions routes candidates candidate sessions routes current task routes workflows."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_current_task_logic_routes import (
    build_current_task_view,
)
from app.candidates.schemas.candidates_schemas_candidates_candidate_sessions_core_schema import (
    CurrentTaskResponse,
)
from app.shared.auth.principal import Principal
from app.shared.auth.shared_auth_candidate_access_utils import (
    require_candidate_principal,
)
from app.shared.database import get_session

router = APIRouter()


@router.get(
    "/session/{candidate_session_id}/current_task", response_model=CurrentTaskResponse
)
async def get_current_task(
    candidate_session_id: Annotated[int, Path(..., ge=1)],
    request: Request,
    principal: Annotated[Principal, Depends(require_candidate_principal)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> CurrentTaskResponse:
    """Return the current task for a candidate session."""
    return await build_current_task_view(candidate_session_id, request, principal, db)
