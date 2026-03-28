"""Application module for tasks routes tasks run poll routes workflows."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.github.actions_runner import GithubActionsRunner
from app.integrations.github.client import GithubError
from app.shared.database import get_session
from app.shared.database.shared_database_models_model import CandidateSession
from app.shared.http.dependencies.shared_http_dependencies_candidate_sessions_utils import (
    candidate_session_from_headers,
)
from app.shared.http.dependencies.shared_http_dependencies_github_native_utils import (
    get_actions_runner,
)
from app.shared.http.shared_http_error_utils import map_github_error
from app.submissions.schemas.submissions_schemas_submissions_core_schema import (
    RunTestsResponse,
)
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)
from app.submissions.services.use_cases.submissions_services_use_cases_submissions_use_cases_fetch_run_service import (
    fetch_run_result,
)
from app.tasks.routes.tasks.tasks_routes_tasks_tasks_run_response_utils import (
    build_run_response,
)

router = APIRouter()


@router.get(
    "/{task_id}/run/{run_id}",
    response_model=RunTestsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_run_result_route(
    task_id: Annotated[int, Path(..., ge=1)],
    run_id: Annotated[int, Path(..., ge=1)],
    db: Annotated[AsyncSession, Depends(get_session)],
    actions_runner: Annotated[GithubActionsRunner, Depends(get_actions_runner)],
    candidate_session: Annotated[
        CandidateSession, Depends(candidate_session_from_headers)
    ],
) -> RunTestsResponse:
    """Poll a previously-triggered workflow run."""
    try:
        task, workspace, result = await fetch_run_result(
            db,
            candidate_session=candidate_session,
            task_id=task_id,
            run_id=run_id,
            runner=actions_runner,
        )
    except GithubError as exc:
        raise map_github_error(exc) from exc

    await submission_service.record_run_result(db, workspace, result)
    return build_run_response(result)
