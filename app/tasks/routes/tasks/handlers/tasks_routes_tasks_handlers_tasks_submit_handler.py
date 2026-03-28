"""Application module for tasks routes tasks handlers tasks submit handler workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions.repositories import repository as cs_repo
from app.integrations.github import GithubClient, GithubError
from app.integrations.github.actions_runner import GithubActionsRunner
from app.shared.database.shared_database_models_model import CandidateSession
from app.shared.http.shared_http_error_utils import map_github_error
from app.submissions.schemas.submissions_schemas_submissions_core_schema import (
    ProgressSummary,
    SubmissionCreateRequest,
    SubmissionCreateResponse,
)
from app.submissions.services.use_cases.submissions_services_use_cases_submissions_use_cases_submit_task_service import (
    submit_task,
)


async def handle_submit_task(
    task_id: int,
    payload: SubmissionCreateRequest,
    candidate_session: CandidateSession,
    db: AsyncSession,
    github_client: GithubClient,
    actions_runner: GithubActionsRunner,
) -> SubmissionCreateResponse:
    """Handle submit task."""
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

    day_audit = None
    if int(getattr(task, "day_index", 0)) in {2, 3}:
        day_audit = await cs_repo.get_day_audit(
            db,
            candidate_session_id=candidate_session.id,
            day_index=task.day_index,
        )
    cutoff_commit_sha = getattr(day_audit, "cutoff_commit_sha", None)
    resolved_commit_sha = cutoff_commit_sha or getattr(submission, "commit_sha", None)
    cutoff_at = getattr(day_audit, "cutoff_at", None)
    if isinstance(cutoff_at, datetime) and cutoff_at.tzinfo is None:
        cutoff_at = cutoff_at.replace(tzinfo=UTC)

    return SubmissionCreateResponse(
        submissionId=submission.id,
        taskId=task.id,
        candidateSessionId=candidate_session.id,
        submittedAt=submission.submitted_at,
        commitSha=resolved_commit_sha,
        cutoffCommitSha=cutoff_commit_sha,
        cutoffAt=cutoff_at,
        evalBasisRef=getattr(day_audit, "eval_basis_ref", None),
        checkpointSha=getattr(submission, "checkpoint_sha", None),
        finalSha=getattr(submission, "final_sha", None),
        progress=ProgressSummary(completed=completed, total=total),
        isComplete=is_complete,
    )
