from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from app.api.dependencies.github_native import get_github_client
from app.domains.github_native import GithubClient
from app.domains.github_native.template_health import (
    TemplateHealthResponse,
    check_template_health,
)
from app.infra.config import settings
from app.infra.security.current_user import get_current_user
from app.infra.security.roles import ensure_recruiter_or_none

router = APIRouter()


@router.get(
    "/templates/health",
    response_model=TemplateHealthResponse,
    status_code=status.HTTP_200_OK,
)
async def get_template_health(
    user: Annotated[Any, Depends(get_current_user)],
    github_client: Annotated[GithubClient, Depends(get_github_client)],
) -> TemplateHealthResponse:
    """Check template repos against the Actions artifact contract (recruiter-only)."""
    ensure_recruiter_or_none(user)
    return await check_template_health(
        github_client,
        workflow_file=settings.github.GITHUB_ACTIONS_WORKFLOW_FILE,
    )
