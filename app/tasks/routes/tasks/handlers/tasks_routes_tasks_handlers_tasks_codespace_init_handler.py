"""Application module for tasks routes tasks handlers tasks codespace init handler workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.github import GithubClient, GithubError
from app.shared.database.shared_database_models_model import CandidateSession
from app.shared.http.shared_http_error_utils import map_github_error
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
            template_owner=settings.github.GITHUB_TEMPLATE_OWNER
            or settings.github.GITHUB_ORG,
            now=datetime.now(UTC),
        )
    except GithubError as exc:
        raise map_github_error(exc) from exc

    return CodespaceInitResponse(
        repoFullName=workspace.repo_full_name,
        repoUrl=f"https://github.com/{workspace.repo_full_name}",
        codespaceUrl=codespace_url,
        defaultBranch=workspace.default_branch,
        baseTemplateSha=getattr(workspace, "base_template_sha", None),
        precommitSha=getattr(workspace, "precommit_sha", None),
        workspaceId=workspace.id,
    )
