"""Application module for tasks routes tasks run routes workflows."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.github.actions_runner import GithubActionsRunner
from app.shared.database import get_session
from app.shared.database.shared_database_models_model import CandidateSession
from app.shared.http.dependencies.shared_http_dependencies_candidate_sessions_utils import (
    candidate_session_from_headers,
)
from app.shared.http.dependencies.shared_http_dependencies_github_native_utils import (
    get_actions_runner,
)
from app.submissions.schemas.submissions_schemas_submissions_core_schema import (
    RunTestsRequest,
    RunTestsResponse,
)
from app.tasks.routes.tasks.handlers import handle_run_tests

router = APIRouter()


@router.post(
    "/{task_id}/run", response_model=RunTestsResponse, status_code=status.HTTP_200_OK
)
async def run_task_tests_route(
    task_id: Annotated[int, Path(..., ge=1)],
    payload: RunTestsRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    actions_runner: Annotated[GithubActionsRunner, Depends(get_actions_runner)],
    candidate_session: Annotated[
        CandidateSession, Depends(candidate_session_from_headers)
    ],
) -> RunTestsResponse:
    """Dispatch GitHub Actions tests for a candidate task."""
    return await handle_run_tests(
        task_id=task_id,
        payload=payload,
        db=db,
        actions_runner=actions_runner,
        candidate_session=candidate_session,
    )
