from __future__ import annotations

import base64
from typing import Any

from app.core.brand import TEST_ARTIFACT_NAMESPACE
from app.domains.common.base import APIModel
from app.domains.github_native import GithubClient, GithubError
from app.domains.github_native.artifacts import PREFERRED_ARTIFACT_NAMES
from app.domains.tasks.template_catalog import TEMPLATE_CATALOG

WORKFLOW_DIR = ".github/workflows"


class TemplateHealthChecks(APIModel):
    """Per-template health check details."""

    repoReachable: bool = False
    defaultBranch: str | None = None
    defaultBranchUsable: bool = False
    workflowFileExists: bool = False
    workflowHasUploadArtifact: bool = False
    workflowHasArtifactName: bool = False
    workflowHasTestResultsJson: bool = False


class TemplateHealthItem(APIModel):
    """Health status for a single template repo."""

    templateKey: str
    repoFullName: str
    workflowFile: str
    defaultBranch: str | None
    ok: bool
    errors: list[str]
    checks: TemplateHealthChecks


class TemplateHealthResponse(APIModel):
    """Aggregate health status for all templates."""

    ok: bool
    templates: list[TemplateHealthItem]


def _workflow_contract_checks(content: str) -> dict[str, bool]:
    text = content.lower()
    has_upload_artifact = "actions/upload-artifact" in text
    has_artifact_name = any(name.lower() in text for name in PREFERRED_ARTIFACT_NAMES)
    has_test_results_json = f"{TEST_ARTIFACT_NAMESPACE}.json" in text
    return {
        "workflowHasUploadArtifact": has_upload_artifact,
        "workflowHasArtifactName": has_artifact_name,
        "workflowHasTestResultsJson": has_test_results_json,
    }


def workflow_contract_errors(content: str) -> tuple[list[str], dict[str, bool]]:
    """Return contract errors and checks for a workflow file."""
    checks = _workflow_contract_checks(content)
    errors: list[str] = []
    if not checks["workflowHasUploadArtifact"]:
        errors.append("workflow_missing_upload_artifact")
    if not checks["workflowHasArtifactName"]:
        errors.append("workflow_missing_artifact_name")
    if not checks["workflowHasTestResultsJson"]:
        errors.append("workflow_missing_test_results_json")
    return errors, checks


def _decode_contents(payload: dict[str, Any]) -> str | None:
    content = payload.get("content")
    encoding = payload.get("encoding")
    if not content:
        return None
    if encoding == "base64":
        try:
            return base64.b64decode(content).decode("utf-8", errors="replace")
        except (ValueError, UnicodeDecodeError):
            return None
    if isinstance(content, str):
        return content
    return None


async def check_template_health(
    github_client: GithubClient,
    *,
    workflow_file: str,
) -> TemplateHealthResponse:
    """Validate all template repos against the Actions artifact contract."""
    items: list[TemplateHealthItem] = []
    for template_key, info in TEMPLATE_CATALOG.items():
        item = await _check_template_repo(
            github_client,
            template_key=template_key,
            repo_full_name=info["repo_full_name"],
            workflow_file=workflow_file,
        )
        items.append(item)
    return TemplateHealthResponse(
        ok=all(item.ok for item in items),
        templates=items,
    )


async def _check_template_repo(
    github_client: GithubClient,
    *,
    template_key: str,
    repo_full_name: str,
    workflow_file: str,
) -> TemplateHealthItem:
    errors: list[str] = []
    checks = TemplateHealthChecks()
    default_branch = None
    workflow_path = f"{WORKFLOW_DIR}/{workflow_file}"

    try:
        repo = await github_client.get_repo(repo_full_name)
        checks.repoReachable = True
    except GithubError as exc:
        if exc.status_code == 404:
            errors.append("repo_not_found")
        else:
            errors.append("repo_unreachable")
        return TemplateHealthItem(
            templateKey=template_key,
            repoFullName=repo_full_name,
            workflowFile=workflow_file,
            defaultBranch=None,
            ok=False,
            errors=errors,
            checks=checks,
        )

    default_branch = (repo.get("default_branch") or "").strip() or None
    checks.defaultBranch = default_branch
    if not default_branch:
        errors.append("default_branch_missing")
    else:
        try:
            await github_client.get_branch(repo_full_name, default_branch)
            checks.defaultBranchUsable = True
        except GithubError:
            errors.append("default_branch_unusable")

    if default_branch:
        try:
            contents = await github_client.get_file_contents(
                repo_full_name, workflow_path, ref=default_branch
            )
            decoded = _decode_contents(contents)
            if not decoded:
                errors.append("workflow_file_unreadable")
            else:
                checks.workflowFileExists = True
                contract_errors, contract_checks = workflow_contract_errors(decoded)
                checks.workflowHasUploadArtifact = contract_checks[
                    "workflowHasUploadArtifact"
                ]
                checks.workflowHasArtifactName = contract_checks[
                    "workflowHasArtifactName"
                ]
                checks.workflowHasTestResultsJson = contract_checks[
                    "workflowHasTestResultsJson"
                ]
                errors.extend(contract_errors)
        except GithubError as exc:
            if exc.status_code == 404:
                errors.append("workflow_file_missing")
            else:
                errors.append("workflow_file_unreadable")

    return TemplateHealthItem(
        templateKey=template_key,
        repoFullName=repo_full_name,
        workflowFile=workflow_file,
        defaultBranch=default_branch,
        ok=len(errors) == 0,
        errors=errors,
        checks=checks,
    )
