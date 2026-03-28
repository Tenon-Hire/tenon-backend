"""Application module for integrations github template health github template health repo result service workflows."""

from __future__ import annotations

from app.integrations.github.template_health.integrations_github_template_health_github_template_health_item_builder_service import (
    build_item,
)
from app.integrations.github.template_health.integrations_github_template_health_github_template_health_live_result_model import (
    LiveCheckResult,
)
from app.integrations.github.template_health.integrations_github_template_health_github_template_health_schema import (
    RunMode,
    TemplateHealthChecks,
)


def build_repo_result(
    template_key: str,
    repo_full_name: str,
    workflow_file: str,
    checks: TemplateHealthChecks,
    errors: list[str],
    mode: RunMode,
    default_branch: str | None,
    live_result: LiveCheckResult | None,
):
    """Build repo result."""
    return build_item(
        template_key,
        repo_full_name,
        workflow_file,
        checks,
        errors,
        mode,
        default_branch=default_branch,
        workflow_run_id=live_result.workflow_run_id if live_result else None,
        workflow_conclusion=live_result.workflow_conclusion if live_result else None,
        artifact_name_found=live_result.artifact_name_found if live_result else None,
    )
