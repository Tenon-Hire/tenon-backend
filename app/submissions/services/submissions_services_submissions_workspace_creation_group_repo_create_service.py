"""Application module for submissions services submissions workspace creation group repo create service workflows."""

from __future__ import annotations

from app.integrations.github.client import GithubClient
from app.shared.database.shared_database_models_model import CandidateSession, Task
from app.submissions.services.submissions_services_submissions_repo_naming_service import (
    build_repo_name as build_task_repo_name,
)
from app.submissions.services.submissions_services_submissions_workspace_bootstrap_service import (
    bootstrap_empty_candidate_repo,
    build_candidate_repo_name,
)


async def create_group_repo(
    *,
    candidate_session: CandidateSession,
    task: Task,
    workspace_key: str,
    github_client: GithubClient,
    repo_prefix: str,
    destination_owner: str | None,
    bootstrap_empty_repo: bool = False,
    trial=None,
    scenario_version=None,
):
    """Create group repo."""
    _ = bootstrap_empty_repo
    if trial is None or scenario_version is None:
        raise ValueError("trial and scenario_version are required for repo bootstrap")
    repo_name = (
        build_candidate_repo_name(repo_prefix, candidate_session)
        if bootstrap_empty_repo
        else build_task_repo_name(
            prefix=repo_prefix,
            candidate_session=candidate_session,
            task=task,
            workspace_key=workspace_key,
        )
    )
    return await bootstrap_empty_candidate_repo(
        github_client=github_client,
        candidate_session=candidate_session,
        trial=trial,
        scenario_version=scenario_version,
        task=task,
        repo_prefix=repo_prefix,
        destination_owner=destination_owner,
        repo_name=repo_name,
    )
