"""Application module for tasks routes tasks handlers tasks codespace init handler workflows."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.github import GithubClient, GithubError
from app.shared.database.shared_database_models_model import CandidateSession
from app.shared.http.shared_http_error_utils import map_github_error
from app.shared.time.shared_time_now_service import utcnow as shared_utcnow
from app.submissions.schemas.submissions_schemas_submissions_core_schema import (
    CodespaceInitRequest,
    CodespaceInitResponse,
)
from app.submissions.services.use_cases.submissions_services_use_cases_submissions_use_cases_codespace_init_service import (
    init_codespace,
)


async def handle_codespace_init(
    task_id: int,
    payload: CodespaceInitRequest,
    candidate_session: CandidateSession,
    db: AsyncSession,
    github_client: GithubClient,
) -> CodespaceInitResponse:
    """Handle codespace init."""
    try:
        workspace, _, codespace_url, _ = await init_codespace(
            db,
            candidate_session=candidate_session,
            task_id=task_id,
            github_client=github_client,
            github_username=payload.githubUsername,
            repo_prefix=settings.github.GITHUB_REPO_PREFIX,
            destination_owner=settings.github.GITHUB_ORG,
            now=shared_utcnow(),
        )
    except GithubError as exc:
        raise map_github_error(exc) from exc

    public_repo_full_name = workspace.repo_full_name
    if getattr(workspace, "workspace_group_id", None) is not None:
        public_repo_full_name = (
            f"{settings.github.GITHUB_ORG}/{settings.github.GITHUB_REPO_PREFIX}"
            f"{candidate_session.id}"
        )

    return CodespaceInitResponse(
        repoFullName=public_repo_full_name,
        codespaceUrl=codespace_url,
        codespaceState=getattr(workspace, "codespace_state", None),
        defaultBranch=workspace.default_branch,
        workspaceId=workspace.id,
    )
