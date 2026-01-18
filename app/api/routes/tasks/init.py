from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.candidate_sessions import candidate_session_from_headers
from app.api.dependencies.github_native import get_github_client
from app.api.error_utils import map_github_error
from app.domains import CandidateSession
from app.domains.github_native import GithubClient, GithubError
from app.domains.submissions.schemas import CodespaceInitRequest, CodespaceInitResponse
from app.domains.submissions.use_cases.codespace_init import init_codespace
from app.infra.config import settings
from app.infra.db import get_session

router = APIRouter()


@router.post(
    "/{task_id}/codespace/init",
    response_model=CodespaceInitResponse,
    status_code=status.HTTP_200_OK,
)
async def init_codespace_route(
    task_id: Annotated[int, Path(..., ge=1)],
    payload: CodespaceInitRequest,
    candidate_session: Annotated[
        CandidateSession, Depends(candidate_session_from_headers)
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
    github_client: Annotated[GithubClient, Depends(get_github_client)],
) -> CodespaceInitResponse:
    """Provision or return a GitHub Codespace workspace for a task."""
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
        workspaceId=workspace.id,
    )
