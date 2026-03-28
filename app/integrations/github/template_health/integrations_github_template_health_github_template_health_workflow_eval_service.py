"""Application module for integrations github template health github template health workflow eval service workflows."""

from __future__ import annotations

from app.integrations.github import GithubClient, GithubError
from app.integrations.github.template_health.integrations_github_template_health_github_template_health_classify_service import (
    _classify_github_error,
)
from app.integrations.github.template_health.integrations_github_template_health_github_template_health_content_decode_service import (
    _decode_contents,
)
from app.integrations.github.template_health.integrations_github_template_health_github_template_health_contract_checks_service import (
    workflow_contract_errors,
)
from app.integrations.github.template_health.integrations_github_template_health_github_template_health_schema import (
    TemplateHealthChecks,
)


async def validate_workflow(
    github_client: GithubClient,
    *,
    repo_full_name: str,
    workflow_path: str,
    default_branch: str,
    checks: TemplateHealthChecks,
    errors: list[str],
) -> None:
    """Validate workflow."""
    try:
        contents = await github_client.get_file_contents(
            repo_full_name, workflow_path, ref=default_branch
        )
        decoded = _decode_contents(contents)
        if not decoded:
            errors.append("workflow_file_unreadable")
            return
        checks.workflowFileExists = True
        contract_errors, contract_checks = workflow_contract_errors(decoded)
        checks.workflowHasUploadArtifact = contract_checks["workflowHasUploadArtifact"]
        checks.workflowHasArtifactName = contract_checks["workflowHasArtifactName"]
        checks.workflowHasTestResultsJson = contract_checks[
            "workflowHasTestResultsJson"
        ]
        errors.extend(contract_errors)
    except GithubError as exc:
        errors.append(
            "workflow_file_missing"
            if exc.status_code == 404
            else _classify_github_error(exc) or "workflow_file_unreadable"
        )
