"""Application module for submissions services submissions workspace creation group repo create service workflows."""

from __future__ import annotations

from app.integrations.github.client import GithubClient
from app.shared.database.shared_database_models_model import CandidateSession, Task
from app.submissions.services.submissions_services_submissions_workspace_template_repo_service import (
    generate_template_repo,
)


async def create_group_repo(
    *,
    candidate_session: CandidateSession,
    task: Task,
    workspace_key: str,
    github_client: GithubClient,
    repo_prefix: str,
    template_default_owner: str | None,
):
    """Create group repo."""
    return await generate_template_repo(
        github_client=github_client,
        candidate_session=candidate_session,
        task=task,
        repo_prefix=repo_prefix,
        template_default_owner=template_default_owner,
        workspace_key=workspace_key,
    )
