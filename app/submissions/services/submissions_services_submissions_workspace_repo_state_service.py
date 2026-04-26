"""Application module for submissions services submissions workspace repo state service workflows."""

from __future__ import annotations

import contextlib

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.github.client import GithubClient, GithubError
from app.submissions.repositories.github_native.workspaces import (
    submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_mutations_repository as workspace_mutations_repo,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    Workspace,
)


async def fetch_base_template_sha(
    github_client: GithubClient, repo_full_name: str, default_branch: str | None
) -> str | None:
    """Return base template sha."""
    try:
        branch_data = await github_client.get_branch(
            repo_full_name, default_branch or "main"
        )
        return (branch_data.get("commit") or {}).get("sha")
    except GithubError:
        return None


async def add_collaborator_if_needed(
    github_client: GithubClient, repo_full_name: str, github_username: str | None
):
    """Add collaborator if needed."""
    if not github_username:
        return
    with contextlib.suppress(GithubError):
        await github_client.add_collaborator(repo_full_name, github_username)


async def ensure_repo_is_active(
    github_client: GithubClient, repo_full_name: str
) -> dict | None:
    """Return a live repository payload, unarchiving archived repos when possible."""
    get_repo = getattr(github_client, "get_repo", None)
    if not callable(get_repo):
        return None

    repo = await get_repo(repo_full_name)
    if not isinstance(repo, dict):
        return repo
    if not repo.get("archived"):
        return repo

    unarchive_repo = getattr(github_client, "unarchive_repo", None)
    if not callable(unarchive_repo):
        return repo

    refreshed = await unarchive_repo(repo_full_name)
    return refreshed if isinstance(refreshed, dict) else repo


async def refresh_codespace_state(
    db: AsyncSession,
    *,
    workspace: Workspace,
    github_client: GithubClient,
) -> Workspace:
    """Refresh and persist the live Codespace state for a workspace."""
    codespace_name = (getattr(workspace, "codespace_name", None) or "").strip()
    repo_full_name = (getattr(workspace, "repo_full_name", None) or "").strip()
    if not codespace_name or not repo_full_name:
        return workspace

    get_codespace = getattr(github_client, "get_codespace", None)
    if not callable(get_codespace):
        return workspace

    try:
        codespace = await get_codespace(repo_full_name, codespace_name)
    except GithubError:
        return workspace

    codespace_state = str(codespace.get("state") or "").strip().lower() or None
    if (
        not codespace_state
        or getattr(workspace, "codespace_state", None) == codespace_state
    ):
        return workspace
    return await workspace_mutations_repo.set_codespace_state(
        db,
        workspace=workspace,
        codespace_state=codespace_state,
    )
