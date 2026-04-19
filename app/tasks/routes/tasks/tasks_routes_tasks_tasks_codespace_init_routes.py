"""Application module for tasks routes tasks codespace init routes workflows."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.github import GithubClient
from app.shared.database import get_session
from app.shared.database.shared_database_models_model import CandidateSession
from app.shared.http.dependencies.shared_http_dependencies_candidate_sessions_utils import (
    candidate_session_from_headers,
)
from app.shared.http.dependencies.shared_http_dependencies_github_native_utils import (
    get_github_client,
)
from app.submissions.schemas.submissions_schemas_submissions_core_schema import (
    CodespaceInitRequest,
    CodespaceInitResponse,
)
from app.tasks.routes.tasks.handlers import handle_codespace_init

router = APIRouter()


@router.post(
    "/{task_id}/codespace/init",
    response_model=CodespaceInitResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
)
async def init_codespace_route(
    task_id: Annotated[int, Path(..., ge=1)],
    payload: CodespaceInitRequest,
    candidate_session: Annotated[
        CandidateSession, Depends(candidate_session_from_headers)
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
    github_client: Annotated[GithubClient, Depends(get_github_client)],
) -> CodespaceInitResponse:
    """Provision or return a GitHub Codespace workspace for a task."""
    return await handle_codespace_init(
        task_id=task_id,
        payload=payload,
        candidate_session=candidate_session,
        db=db,
        github_client=github_client,
    )
