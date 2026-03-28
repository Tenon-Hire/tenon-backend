"""Application module for submissions services use cases submissions use cases submit task runner service workflows."""

from __future__ import annotations

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.github.client import GithubClient, GithubError
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    Workspace,
)
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)
from app.submissions.services.submissions_services_submissions_run_service import (
    ActionsRunResult,
)
from app.submissions.services.use_cases.submissions_services_use_cases_submissions_use_cases_submit_diff_service import (
    build_diff_summary,
)
from app.submissions.services.use_cases.submissions_services_use_cases_submissions_use_cases_submit_workspace_service import (
    fetch_workspace_and_branch,
)


async def run_code_submission(
    *,
    db: AsyncSession,
    candidate_session_id: int,
    task_id: int,
    task_day_index: int | None = None,
    task_type: str | None = None,
    payload,
    github_client: GithubClient,
    actions_runner,
) -> tuple[ActionsRunResult | None, str | None, Workspace | None]:
    """Run code submission."""
    workspace, branch = await fetch_workspace_and_branch(
        db,
        candidate_session_id,
        task_id,
        payload,
        task_day_index=task_day_index,
        task_type=task_type,
    )
    try:
        actions_result = await submission_service.run_actions_tests(
            runner=actions_runner,
            workspace=workspace,
            branch=branch or "main",
            workflow_inputs=getattr(payload, "workflowInputs", None),
        )
        await submission_service.record_run_result(db, workspace, actions_result)
        if not actions_result.head_sha:
            return actions_result, None, workspace
        diff_summary_json = await build_diff_summary(
            github_client, workspace, branch, actions_result.head_sha
        )
        return actions_result, diff_summary_json, workspace
    except GithubError:
        raise
    except Exception as exc:  # pragma: no cover - safety net
        raise ApiError(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub unavailable. Please try again.",
            error_code="GITHUB_UNAVAILABLE",
            retryable=True,
        ) from exc
