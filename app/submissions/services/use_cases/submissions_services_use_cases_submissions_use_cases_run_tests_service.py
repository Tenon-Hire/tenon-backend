"""Application module for submissions services use cases submissions use cases run tests service workflows."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions import services as cs_service
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
)
from app.submissions.services.use_cases.submissions_services_use_cases_submissions_use_cases_day_flow_gate_service import (
    ensure_day_flow_open,
)


async def run_task_tests(
    db: AsyncSession,
    *,
    candidate_session: CandidateSession,
    task_id: int,
    runner: GithubActionsRunner,
    branch: str | None,
    workflow_inputs: dict | None,
):
    """Dispatch workflow run for the task and return result."""
    apply_rate_limit(candidate_session.id, "run")
    task = await submission_service.load_task_or_404(db, task_id)
    submission_service.ensure_task_belongs(task, candidate_session)
    cs_service.require_active_window(candidate_session, task)
    await ensure_day_flow_open(db, candidate_session=candidate_session, task=task)
    submission_service.validate_run_allowed(task)

    workspace = await submission_service.workspace_repo.get_by_session_and_task(
        db, candidate_session_id=candidate_session.id, task_id=task.id
    )
    if workspace is None:
        raise WorkspaceMissing()
    branch_to_use = submission_service.validate_branch(
        branch or workspace.default_branch or "main"
    )
    async with concurrency_guard(candidate_session.id, "dispatch"):
        return (
            task,
            workspace,
            await submission_service.run_actions_tests(
                runner=runner,
                workspace=workspace,
                branch=branch_to_use or "main",
                workflow_inputs=workflow_inputs,
            ),
        )
