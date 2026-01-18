from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.candidate_sessions import candidate_session_from_headers
from app.api.dependencies.github_native import get_actions_runner, get_github_client
from app.api.error_utils import map_github_error
from app.domains import CandidateSession
from app.domains.github_native import GithubClient, GithubError
from app.domains.github_native.actions_runner import GithubActionsRunner
from app.domains.submissions.schemas import (
    ProgressSummary,
    SubmissionCreateRequest,
    SubmissionCreateResponse,
)
from app.domains.submissions.use_cases.submit_task import submit_task
from app.infra.db import get_session

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
    """Submit a task, optionally running GitHub tests for code/debug types."""
    try:
        task, submission, completed, total, is_complete = await submit_task(
            db,
            candidate_session=candidate_session,
            task_id=task_id,
            payload=payload,
            github_client=github_client,
            actions_runner=actions_runner,
        )
    except GithubError as exc:
        raise map_github_error(exc) from exc

    return SubmissionCreateResponse(
        submissionId=submission.id,
        taskId=task.id,
        candidateSessionId=candidate_session.id,
        submittedAt=submission.submitted_at,
        progress=ProgressSummary(completed=completed, total=total),
        isComplete=is_complete,
    )
