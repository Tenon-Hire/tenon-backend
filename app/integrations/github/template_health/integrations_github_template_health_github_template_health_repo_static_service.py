"""Application module for integrations github template health github template health repo static service workflows."""

from __future__ import annotations

from app.integrations.github import GithubClient
from app.integrations.github.template_health.integrations_github_template_health_github_template_health_repo_fetch_service import (
    fetch_repo_and_branch,
)
from app.integrations.github.template_health.integrations_github_template_health_github_template_health_schema import (
    WORKFLOW_DIR,
    TemplateHealthChecks,
)
from app.integrations.github.template_health.integrations_github_template_health_github_template_health_workflow_eval_service import (
    validate_workflow,
)


async def run_static_checks(
    github_client: GithubClient,
    *,
    repo_full_name: str,
    workflow_file: str,
    checks: TemplateHealthChecks,
    errors: list[str],
) -> str | None:
    """Run static checks."""
    default_branch = await fetch_repo_and_branch(
        github_client, repo_full_name, checks, errors
    )
    if default_branch:
        workflow_path = f"{WORKFLOW_DIR}/{workflow_file}"
        await validate_workflow(
            github_client,
            repo_full_name=repo_full_name,
            workflow_path=workflow_path,
            default_branch=default_branch,
            checks=checks,
            errors=errors,
        )
    return default_branch
