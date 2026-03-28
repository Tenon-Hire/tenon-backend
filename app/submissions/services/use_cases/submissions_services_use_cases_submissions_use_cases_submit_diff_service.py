"""Application module for submissions services use cases submissions use cases submit diff service workflows."""

from __future__ import annotations

import json

from app.integrations.github.client import GithubClient
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    Workspace,
)
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)


async def build_diff_summary(
    github_client: GithubClient, workspace: Workspace, branch: str, head_sha: str
) -> str | None:
    """Build diff summary."""
    base_sha = workspace.base_template_sha or branch
    compare = await github_client.get_compare(
        workspace.repo_full_name, base_sha, head_sha
    )
    return json.dumps(
        submission_service.summarize_diff(compare, base=base_sha, head=head_sha),
        ensure_ascii=False,
    )
