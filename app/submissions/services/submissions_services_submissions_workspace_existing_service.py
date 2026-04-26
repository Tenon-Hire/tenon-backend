"""Application module for submissions services submissions workspace existing service workflows."""

from __future__ import annotations

import contextlib

from app.integrations.github.client import GithubClient, GithubError
from app.shared.database.shared_database_models_model import CandidateSession, Task
from app.submissions.repositories.github_native.workspaces import (
    submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_repository as workspace_repo,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    Workspace,
)


async def ensure_existing_workspace(
    db,
    *,
    candidate_session: CandidateSession,
    task: Task,
    github_client: GithubClient,
    github_username: str | None,
    workspace_resolution: workspace_repo.WorkspaceResolution | None = None,
    commit: bool = True,
    hydrate_bundle: bool = True,
) -> Workspace | None:
    """Ensure existing workspace."""
    task_day_index = getattr(task, "day_index", None)
    task_type = getattr(task, "type", None)
    task_identity: dict[str, int | str] = {}
    if task_day_index is not None and task_type is not None:
        task_identity["task_day_index"] = task_day_index
        task_identity["task_type"] = task_type
    existing = await workspace_repo.get_by_session_and_task(
        db,
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        workspace_resolution=workspace_resolution,
        **task_identity,
    )
    if not existing:
        return None
    if github_username:
        with contextlib.suppress(GithubError):
            await github_client.add_collaborator(
                existing.repo_full_name, github_username
            )
    _ = (commit, hydrate_bundle)
    return existing
