"""Application module for tasks routes tasks codespace status routes workflows."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions.repositories import repository as cs_repo
from app.config import settings
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
    CodespaceStatusResponse,
)
from app.submissions.services.use_cases.submissions_services_use_cases_submissions_use_cases_codespace_status_service import (
    codespace_status,
)

router = APIRouter()


@router.get(
    "/{task_id}/codespace/status",
    response_model=CodespaceStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def codespace_status_route(
    task_id: Annotated[int, Path(..., ge=1)],
    candidate_session: Annotated[
        CandidateSession, Depends(candidate_session_from_headers)
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
    github_client: Annotated[GithubClient, Depends(get_github_client)],
) -> CodespaceStatusResponse:
    """Return Codespace details and last known test status for a task."""
    workspace, last_test_summary, codespace_url, task = await codespace_status(
        db,
        candidate_session=candidate_session,
        task_id=task_id,
        github_client=github_client,
    )
    day_audit = await cs_repo.get_day_audit(
        db,
        candidate_session_id=candidate_session.id,
        day_index=task.day_index,
    )
    cutoff_commit_sha = getattr(day_audit, "cutoff_commit_sha", None)
    cutoff_at = getattr(day_audit, "cutoff_at", None)
    if isinstance(cutoff_at, datetime) and cutoff_at.tzinfo is None:
        cutoff_at = cutoff_at.replace(tzinfo=UTC)

    public_repo_full_name = workspace.repo_full_name
    if getattr(workspace, "workspace_group_id", None) is not None:
        public_repo_full_name = (
            f"{settings.github.GITHUB_ORG}/{settings.github.GITHUB_REPO_PREFIX}"
            f"{candidate_session.id}"
        )

    return CodespaceStatusResponse(
        repoFullName=public_repo_full_name,
        codespaceUrl=codespace_url,
        codespaceState=getattr(workspace, "codespace_state", None),
        defaultBranch=workspace.default_branch,
        latestCommitSha=workspace.latest_commit_sha,
        lastWorkflowRunId=workspace.last_workflow_run_id,
        lastWorkflowConclusion=workspace.last_workflow_conclusion,
        lastTestSummary=last_test_summary,
        workspaceId=workspace.id,
        cutoffCommitSha=cutoff_commit_sha,
        cutoffAt=cutoff_at,
    )
