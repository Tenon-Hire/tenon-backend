"""Application module for submissions repositories github native workspaces submissions github native workspaces mutations repository workflows."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_core_model import (
    Workspace,
    WorkspaceGroup,
)


async def create_workspace_group(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    workspace_key: str,
    template_repo_full_name: str,
    repo_full_name: str,
    default_branch: str | None,
    base_template_sha: str | None,
    created_at,
    commit: bool = True,
    refresh: bool = True,
) -> WorkspaceGroup:
    """Create workspace group."""
    group = WorkspaceGroup(
        candidate_session_id=candidate_session_id,
        workspace_key=workspace_key,
        template_repo_full_name=template_repo_full_name,
        repo_full_name=repo_full_name,
        default_branch=default_branch,
        base_template_sha=base_template_sha,
        created_at=created_at,
    )
    db.add(group)
    await (db.commit() if commit else db.flush())
    if refresh:
        await db.refresh(group)
    return group


async def create_workspace(
    db: AsyncSession,
    *,
    workspace_group_id: str | None = None,
    candidate_session_id: int,
    task_id: int,
    template_repo_full_name: str,
    repo_full_name: str,
    repo_id: int | None,
    default_branch: str | None,
    base_template_sha: str | None,
    codespace_url: str | None = None,
    precommit_sha: str | None = None,
    precommit_details_json: str | None = None,
    created_at,
    commit: bool = True,
    refresh: bool = True,
) -> Workspace:
    """Create workspace."""
    ws = Workspace(
        workspace_group_id=workspace_group_id,
        candidate_session_id=candidate_session_id,
        task_id=task_id,
        template_repo_full_name=template_repo_full_name,
        repo_full_name=repo_full_name,
        repo_id=repo_id,
        default_branch=default_branch,
        base_template_sha=base_template_sha,
        codespace_url=codespace_url,
        precommit_sha=precommit_sha,
        precommit_details_json=precommit_details_json,
        created_at=created_at,
    )
    db.add(ws)
    await (db.commit() if commit else db.flush())
    if refresh:
        await db.refresh(ws)
    return ws


async def set_precommit_sha(
    db: AsyncSession,
    *,
    workspace: Workspace,
    precommit_sha: str,
    commit: bool = True,
    refresh: bool = True,
) -> Workspace:
    """Set precommit sha."""
    workspace.precommit_sha = precommit_sha
    workspace.precommit_details_json = None
    await (db.commit() if commit else db.flush())
    if refresh:
        await db.refresh(workspace)
    return workspace


async def set_precommit_details(
    db: AsyncSession,
    *,
    workspace: Workspace,
    precommit_details_json: str,
    commit: bool = True,
    refresh: bool = True,
) -> Workspace:
    """Set precommit details."""
    workspace.precommit_details_json = precommit_details_json
    await (db.commit() if commit else db.flush())
    if refresh:
        await db.refresh(workspace)
    return workspace


__all__ = [
    "create_workspace",
    "create_workspace_group",
    "set_precommit_details",
    "set_precommit_sha",
]
