"""Application module for integrations github template health github template health runner service workflows."""

from __future__ import annotations

from app.integrations.github import GithubClient
from app.integrations.github.template_health.integrations_github_template_health_github_template_health_repo_check_service import (
    check_template_repo,
)
from app.integrations.github.template_health.integrations_github_template_health_github_template_health_runner_concurrency_service import (
    run_with_concurrency,
)
from app.integrations.github.template_health.integrations_github_template_health_github_template_health_schema import (
    RunMode,
    TemplateHealthResponse,
)
from app.tasks.services.tasks_services_tasks_template_catalog_service import (
    TEMPLATE_CATALOG,
)


async def check_template_health(
    github_client: GithubClient,
    *,
    workflow_file: str,
    mode: RunMode = "static",
    template_keys: list[str] | None = None,
    timeout_seconds: int = 180,
    concurrency: int = 1,
) -> TemplateHealthResponse:
    """Check template health."""
    selected = template_keys or list(TEMPLATE_CATALOG.keys())
    items = await run_with_concurrency(
        selected,
        concurrency=concurrency,
        worker=lambda key: check_template_repo(
            github_client,
            template_key=key,
            repo_full_name=TEMPLATE_CATALOG[key]["repo_full_name"],
            workflow_file=workflow_file,
            mode=mode,
            timeout_seconds=timeout_seconds,
        ),
    )
    return TemplateHealthResponse(
        ok=all(item.ok for item in items), templates=items, mode=mode
    )
