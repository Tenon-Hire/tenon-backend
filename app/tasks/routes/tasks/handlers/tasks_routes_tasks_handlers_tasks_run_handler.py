"""Application module for tasks routes tasks handlers tasks run handler workflows."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.github.actions_runner import GithubActionsRunner
from app.integrations.github.client import GithubError
from app.shared.database.shared_database_models_model import CandidateSession
from app.shared.http.shared_http_error_utils import map_github_error
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.submissions.schemas.submissions_schemas_submissions_core_schema import (
    RunTestsRequest,
    RunTestsResponse,
)
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)
from app.submissions.services.use_cases.submissions_services_use_cases_submissions_use_cases_run_tests_service import (
    run_task_tests,
)
from app.tasks.routes.tasks.tasks_routes_tasks_tasks_run_response_utils import (
    build_run_response,
)


async def handle_run_tests(
    task_id: int,
    payload: RunTestsRequest,
    db: AsyncSession,
    actions_runner: GithubActionsRunner,
    candidate_session: CandidateSession,
) -> RunTestsResponse:
    """Handle run tests."""
    try:
        _, workspace, result = await run_task_tests(
            db,
            candidate_session=candidate_session,
            task_id=task_id,
            runner=actions_runner,
            branch=payload.branch,
            workflow_inputs=payload.workflowInputs,
        )
    except GithubError as exc:
        raise map_github_error(exc) from exc
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - safety net
        raise ApiError(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub unavailable. Please try again.",
            error_code="GITHUB_UNAVAILABLE",
            retryable=True,
        ) from exc

    await submission_service.record_run_result(db, workspace, result)
    return build_run_response(result)
