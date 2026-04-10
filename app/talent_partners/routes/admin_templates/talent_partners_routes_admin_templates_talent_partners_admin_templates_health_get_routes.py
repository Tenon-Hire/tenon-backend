"""Application module for Talent Partners routes admin templates Talent Partners admin templates health get routes workflows."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.integrations.github import GithubClient
from app.integrations.github.template_health import (
    TemplateHealthResponse,
    check_template_health,
)
from app.shared.auth.shared_auth_admin_api_key_utils import require_admin_key
from app.shared.http.dependencies.shared_http_dependencies_github_native_utils import (
    get_github_client,
)

router = APIRouter()
STATIC_TEMPLATE_HEALTH_CONCURRENCY = 6


@router.get(
    "/templates/health",
    response_model=TemplateHealthResponse,
    status_code=status.HTTP_200_OK,
)
async def get_template_health(
    _: Annotated[None, Depends(require_admin_key)],
    github_client: Annotated[GithubClient, Depends(get_github_client)],
    mode: Literal["static", "live"] = "static",
) -> TemplateHealthResponse:
    """Check template repos against the Actions artifact contract (admin-only)."""
    if mode != "static":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use POST /api/admin/templates/health/run for live checks",
        )
    return await check_template_health(
        github_client,
        workflow_file=settings.github.GITHUB_ACTIONS_WORKFLOW_FILE,
        mode="static",
        concurrency=STATIC_TEMPLATE_HEALTH_CONCURRENCY,
    )
