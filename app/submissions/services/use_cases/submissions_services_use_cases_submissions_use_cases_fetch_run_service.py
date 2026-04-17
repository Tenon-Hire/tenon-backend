"""Application module for submissions services use cases submissions use cases fetch run service workflows."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.github.actions_runner import GithubActionsRunner
from app.shared.database.shared_database_models_model import CandidateSession
from app.submissions.constants.submissions_constants_submissions_exceptions_constants import (
    WorkspaceMissing,
)
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)
from app.submissions.services.submissions_services_submissions_rate_limits_constants import (
    apply_rate_limit,
    concurrency_guard,
    throttle_poll,
)
from app.submissions.services.use_cases.submissions_services_use_cases_submissions_use_cases_day_flow_gate_service import (
    ensure_day_flow_open,
)


async def fetch_run_result(
    db: AsyncSession,
    *,
    candidate_session: CandidateSession,
    task_id: int,
    run_id: int,
    runner: GithubActionsRunner,
):
    """Fetch a specific workflow run result for polling."""
    apply_rate_limit(candidate_session.id, "poll")
    throttle_poll(candidate_session.id, run_id)
    task = await submission_service.load_task_or_404(db, task_id)
    submission_service.ensure_task_belongs(task, candidate_session)
    await ensure_day_flow_open(db, candidate_session=candidate_session, task=task)
    submission_service.validate_run_allowed(task)

    workspace = await submission_service.workspace_repo.get_by_session_and_task(
        db, candidate_session_id=candidate_session.id, task_id=task.id
    )
    if workspace is None:
        raise WorkspaceMissing()
    async with concurrency_guard(candidate_session.id, "fetch"):
        return (
            task,
            workspace,
            await runner.fetch_run_result(
                repo_full_name=workspace.repo_full_name, run_id=run_id
            ),
        )
