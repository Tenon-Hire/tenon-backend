"""Application module for submissions services submissions workspace creation grouped hydration service workflows."""

from __future__ import annotations

from app.integrations.github.client import GithubClient
from app.shared.database.shared_database_models_model import CandidateSession, Task
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    Workspace,
)
from app.submissions.services.submissions_services_submissions_workspace_repo_state_service import (
    add_collaborator_if_needed,
)


async def hydrate_existing_workspace(
    db,
    workspace: Workspace,
    candidate_session: CandidateSession,
    task: Task,
    github_client: GithubClient,
    github_username: str | None,
    hydrate_bundle: bool,
    commit: bool,
    ensure_collaborator: bool = False,
) -> Workspace:
    """Hydrate existing workspace."""
    if ensure_collaborator:
        await add_collaborator_if_needed(
            github_client, workspace.repo_full_name, github_username
        )
    _ = (db, candidate_session, task, hydrate_bundle, commit)
    return workspace
