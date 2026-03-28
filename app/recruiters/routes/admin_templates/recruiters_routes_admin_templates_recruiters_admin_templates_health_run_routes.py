"""Admin route for executing live GitHub template health checks on demand."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.config import settings
from app.integrations.github import GithubClient
from app.integrations.github.template_health import (
    TemplateHealthResponse,
    check_template_health,
)
from app.recruiters.routes.admin_templates.recruiters_routes_admin_templates_recruiters_admin_templates_schemas_routes import (
    TemplateHealthRunRequest,
)
from app.recruiters.routes.admin_templates.recruiters_routes_admin_templates_recruiters_admin_templates_validation_routes import (
    validate_live_request,
)
from app.shared.auth.shared_auth_admin_api_key_utils import require_admin_key
from app.shared.http.dependencies.shared_http_dependencies_github_native_utils import (
    get_github_client,
)

router = APIRouter()


@router.post(
    "/templates/health/run",
    response_model=TemplateHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Run Template Health",
    description=(
        "Execute live template health checks by dispatching workflow runs and"
        " validating artifact contracts."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Invalid or missing admin key."},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Live check payload validation failed."
        },
    },
)
async def run_template_health(
    payload: TemplateHealthRunRequest,
    _: Annotated[None, Depends(require_admin_key)],
    github_client: Annotated[GithubClient, Depends(get_github_client)],
) -> TemplateHealthResponse:
    """Validate input and run live workflow-based template health checks."""
    template_keys, timeout_seconds, concurrency = validate_live_request(payload)
    return await check_template_health(
        github_client,
        workflow_file=settings.github.GITHUB_ACTIONS_WORKFLOW_FILE,
        mode="live",
        template_keys=template_keys,
        timeout_seconds=timeout_seconds,
        concurrency=concurrency,
    )
