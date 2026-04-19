"""Application module for tasks routes tasks submit routes workflows."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.github import GithubClient
from app.integrations.github.actions_runner import GithubActionsRunner
from app.shared.database import get_session
from app.shared.database.shared_database_models_model import CandidateSession
from app.shared.http.dependencies.shared_http_dependencies_candidate_sessions_utils import (
    candidate_session_from_headers,
)
from app.shared.http.dependencies.shared_http_dependencies_github_native_utils import (
    get_actions_runner,
    get_github_client,
)
from app.submissions.schemas.submissions_schemas_submissions_core_schema import (
    SubmissionCreateRequest,
    SubmissionCreateResponse,
)
from app.tasks.routes.tasks.handlers import handle_submit_task

router = APIRouter()


@router.post(
    "/{task_id}/submit",
    response_model=SubmissionCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_task_route(
    task_id: Annotated[int, Path(..., ge=1)],
    payload: SubmissionCreateRequest,
    candidate_session: Annotated[
        CandidateSession, Depends(candidate_session_from_headers)
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
    github_client: Annotated[GithubClient, Depends(get_github_client)],
    actions_runner: Annotated[GithubActionsRunner, Depends(get_actions_runner)],
) -> SubmissionCreateResponse:
    """Submit a task, optionally running GitHub tests for code tasks."""
    return await handle_submit_task(
        task_id=task_id,
        payload=payload,
        candidate_session=candidate_session,
        db=db,
        github_client=github_client,
        actions_runner=actions_runner,
    )
