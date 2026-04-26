"""Application module for submissions services submissions workspace creation group repo service workflows."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.exc import IntegrityError

from app.integrations.github.client import GithubClient, GithubError
from app.shared.database.shared_database_models_model import CandidateSession, Task
from app.submissions.repositories.github_native.workspaces import (
    repository as workspace_repo,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    WorkspaceGroup,
)
from app.submissions.services.submissions_services_submissions_workspace_creation_group_repo_create_service import (
    create_group_repo,
)
from app.submissions.services.submissions_services_submissions_workspace_repo_state_service import (
    add_collaborator_if_needed,
)


async def get_or_create_workspace_group(
    db,
    *,
    candidate_session: CandidateSession,
    task: Task,
    workspace_key: str,
    github_client: GithubClient,
    github_username: str | None,
    repo_prefix: str,
    destination_owner: str | None,
    now: datetime,
    existing_group: WorkspaceGroup | None = None,
    commit: bool = True,
    workspace_group_checked: bool = False,
    bootstrap_empty_repo: bool = False,
    trial=None,
    scenario_version=None,
) -> tuple[WorkspaceGroup, int | None, str | None, str | None, str | None]:
    """Return or create workspace group."""
    existing = existing_group or await _load_existing_group(
        db, candidate_session.id, workspace_key, workspace_group_checked
    )
    if existing is not None:
        await add_collaborator_if_needed(
            github_client, existing.repo_full_name, github_username
        )
        return existing, None, None, None, None
    try:
        created_repo = await create_group_repo(
            candidate_session=candidate_session,
            trial=trial,
            scenario_version=scenario_version,
            task=task,
            workspace_key=workspace_key,
            github_client=github_client,
            repo_prefix=repo_prefix,
            destination_owner=destination_owner,
            bootstrap_empty_repo=bootstrap_empty_repo,
        )
        template_repo = created_repo.template_repo_full_name
        repo_full_name = created_repo.repo_full_name
        default_branch = created_repo.default_branch
        repo_id = created_repo.repo_id
        # Legacy DB column name; this now stores the repo bootstrap commit SHA.
        base_template_sha = created_repo.bootstrap_commit_sha
        codespace_name = created_repo.codespace_name
        codespace_state = created_repo.codespace_state
        codespace_url = created_repo.codespace_url
    except GithubError as exc:
        if exc.status_code == 422:
            existing = await workspace_repo.get_workspace_group(
                db,
                candidate_session_id=candidate_session.id,
                workspace_key=workspace_key,
            )
            if existing is not None:
                await add_collaborator_if_needed(
                    github_client, existing.repo_full_name, github_username
                )
                return existing, None, None, None, None
        raise
    await add_collaborator_if_needed(github_client, repo_full_name, github_username)
    create_group_kwargs = {
        "candidate_session_id": candidate_session.id,
        "workspace_key": workspace_key,
        "template_repo_full_name": template_repo,
        "repo_full_name": repo_full_name,
        "default_branch": default_branch,
        "base_template_sha": base_template_sha,
        "created_at": now,
    }
    if not commit:
        create_group_kwargs["commit"] = False
        create_group_kwargs["refresh"] = False
    try:
        return (
            await workspace_repo.create_workspace_group(db, **create_group_kwargs),
            repo_id,
            codespace_name,
            codespace_state,
            codespace_url,
        )
    except IntegrityError:
        await db.rollback()
        existing = await workspace_repo.get_workspace_group(
            db, candidate_session_id=candidate_session.id, workspace_key=workspace_key
        )
        if existing is None:
            raise
        await add_collaborator_if_needed(
            github_client, existing.repo_full_name, github_username
        )
        return existing, None, None, None, None


async def _load_existing_group(
    db, candidate_session_id: int, workspace_key: str, already_checked: bool
):
    if already_checked:
        return None
    return await workspace_repo.get_workspace_group(
        db, candidate_session_id=candidate_session_id, workspace_key=workspace_key
    )
